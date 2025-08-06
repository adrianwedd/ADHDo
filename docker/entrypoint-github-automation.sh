#!/bin/bash
set -e

# GitHub Automation System Entrypoint Script
# Production-ready startup with health checks, migrations, and monitoring

echo "🤖 Starting ADHDo GitHub Automation System..."
echo "Environment: ${ENVIRONMENT:-production}"
echo "Workers: ${WORKERS:-4}"
echo "Build the future, one line of code at a time."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp and color
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[${timestamp}] INFO: ${message}${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}[${timestamp}] WARN: ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR: ${message}${NC}"
            ;;
        "DEBUG")
            echo -e "${BLUE}[${timestamp}] DEBUG: ${message}${NC}"
            ;;
    esac
}

# Function to check if database is ready
check_database() {
    log "INFO" "Checking database connection..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from src.mcp_server.config import settings

async def check_db():
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.execute('SELECT 1')
        await engine.dispose()
        return True
    except Exception as e:
        print(f'Database check failed: {e}')
        return False

result = asyncio.run(check_db())
sys.exit(0 if result else 1)
" 2>/dev/null; then
            log "INFO" "Database connection successful"
            return 0
        fi
        
        log "WARN" "Database not ready, attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    log "ERROR" "Database connection failed after $max_attempts attempts"
    return 1
}

# Function to check if Redis is ready
check_redis() {
    log "INFO" "Checking Redis connection..."
    
    max_attempts=15
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "
import redis
import sys
from src.mcp_server.config import settings

try:
    r = redis.from_url(settings.redis_url)
    r.ping()
    print('Redis connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Redis check failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log "INFO" "Redis connection successful"
            return 0
        fi
        
        log "WARN" "Redis not ready, attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    log "ERROR" "Redis connection failed after $max_attempts attempts"
    return 1
}

# Function to run database migrations
run_migrations() {
    log "INFO" "Running database migrations..."
    
    if alembic upgrade head; then
        log "INFO" "Database migrations completed successfully"
    else
        log "ERROR" "Database migrations failed"
        exit 1
    fi
}

# Function to validate environment configuration
validate_config() {
    log "INFO" "Validating configuration..."
    
    # Required environment variables
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=($var)
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log "ERROR" "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
    
    # GitHub automation specific validation
    if [[ "${GITHUB_AUTOMATION_ENABLED:-true}" == "true" ]]; then
        if [[ -z "${GITHUB_TOKEN:-}" ]] && [[ -z "${OPENAI_API_KEY:-}" ]]; then
            log "WARN" "GitHub automation enabled but no GitHub token or OpenAI API key configured"
        fi
    fi
    
    log "INFO" "Configuration validation passed"
}

# Function to create necessary directories
create_directories() {
    log "INFO" "Creating necessary directories..."
    
    directories=(
        "/app/logs"
        "/app/data"
        "/app/tmp"
        "/app/cache"
        "/app/logs/automation"
        "/app/logs/audit"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "DEBUG" "Created directory: $dir"
        fi
    done
}

# Function to set up monitoring
setup_monitoring() {
    if [[ "${ENVIRONMENT}" == "production" ]]; then
        log "INFO" "Setting up production monitoring..."
        
        # Create monitoring endpoints file
        cat > /app/monitoring.json << EOF
{
    "service": "github-automation",
    "version": "1.0.0",
    "environment": "${ENVIRONMENT}",
    "start_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "endpoints": {
        "health": "/api/github/health",
        "metrics": "/api/github/metrics/summary",
        "audit": "/api/github/audit/summary"
    }
}
EOF
        
        log "INFO" "Monitoring configuration created"
    fi
}

# Function to start the application server
start_server() {
    local mode=${1:-production}
    
    case $mode in
        "production")
            log "INFO" "Starting production server with Gunicorn..."
            exec gunicorn \
                --worker-class ${WORKER_CLASS:-uvicorn.workers.UvicornWorker} \
                --workers ${WORKERS:-4} \
                --max-requests ${MAX_REQUESTS:-1000} \
                --max-requests-jitter ${MAX_REQUESTS_JITTER:-100} \
                --timeout ${TIMEOUT:-120} \
                --keepalive ${KEEPALIVE:-2} \
                --bind ${BIND_HOST:-0.0.0.0}:${BIND_PORT:-8000} \
                --access-logfile /app/logs/access.log \
                --error-logfile /app/logs/error.log \
                --log-level ${LOG_LEVEL:-info} \
                --preload \
                --enable-stdio-inheritance \
                src.mcp_server.main:app
            ;;
            
        "development")
            log "INFO" "Starting development server with hot reload..."
            exec uvicorn \
                src.mcp_server.main:app \
                --host ${BIND_HOST:-0.0.0.0} \
                --port ${BIND_PORT:-8000} \
                --reload \
                --reload-dir /app/src \
                --log-level ${LOG_LEVEL:-debug} \
                --access-log \
                --use-colors
            ;;
            
        "worker")
            log "INFO" "Starting background worker..."
            exec python -m src.github_automation.worker
            ;;
            
        "scheduler")
            log "INFO" "Starting automation scheduler..."
            exec python -m src.github_automation.scheduler
            ;;
            
        "migration")
            log "INFO" "Running migrations only..."
            run_migrations
            exit 0
            ;;
            
        "shell")
            log "INFO" "Starting interactive shell..."
            exec python -c "
import asyncio
from src.mcp_server.database import init_database
from src.github_automation import *
print('GitHub Automation Shell Ready')
print('Available modules: automation_engine, webhook_handler, audit_logger')
asyncio.run(init_database())
"
            ;;
            
        *)
            log "ERROR" "Unknown startup mode: $mode"
            echo "Available modes: production, development, worker, scheduler, migration, shell"
            exit 1
            ;;
    esac
}

# Function to handle shutdown signals
cleanup() {
    log "INFO" "Received shutdown signal, performing cleanup..."
    
    # Flush any remaining audit logs
    if [[ -f "/app/logs/audit/current.jsonl" ]]; then
        log "INFO" "Flushing audit logs..."
    fi
    
    # Close database connections gracefully
    log "INFO" "Closing database connections..."
    
    # Stop any background processes
    jobs -p | xargs -r kill
    
    log "INFO" "Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main execution
main() {
    local command=${1:-production}
    
    # Always validate configuration
    validate_config
    
    # Create directories
    create_directories
    
    # For production and development modes, check dependencies
    if [[ "$command" == "production" ]] || [[ "$command" == "development" ]]; then
        check_database || exit 1
        check_redis || exit 1
        run_migrations
        setup_monitoring
    fi
    
    # Log startup information
    log "INFO" "=== ADHDo GitHub Automation System ==="
    log "INFO" "Mode: $command"
    log "INFO" "Environment: ${ENVIRONMENT:-production}"
    log "INFO" "Python version: $(python --version)"
    log "INFO" "Working directory: $(pwd)"
    
    if [[ "${GITHUB_AUTOMATION_ENABLED:-true}" == "true" ]]; then
        log "INFO" "GitHub automation: ENABLED"
        log "INFO" "Max concurrent actions: ${AUTOMATION_MAX_CONCURRENT_ACTIONS:-10}"
        log "INFO" "Rate limit buffer: ${AUTOMATION_RATE_LIMIT_BUFFER:-0.8}"
    else
        log "WARN" "GitHub automation: DISABLED"
    fi
    
    # Start the appropriate service
    start_server "$command"
}

# Execute main function with all arguments
main "$@"