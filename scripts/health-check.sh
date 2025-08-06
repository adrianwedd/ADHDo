#!/bin/bash

# MCP ADHD Server - Advanced Health Check Script
# Comprehensive health validation for production deployment

set -e

# Configuration
APP_URL="${APP_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-10}"
RETRIES="${RETRIES:-3}"
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verbose logging
debug() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1" >&2
    fi
}

# Health check function
check_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"
    
    debug "Checking endpoint: $APP_URL$endpoint"
    
    for attempt in $(seq 1 $RETRIES); do
        if response=$(curl -s -w "%{http_code}" --max-time $TIMEOUT "$APP_URL$endpoint" 2>/dev/null); then
            http_code="${response: -3}"
            body="${response%???}"
            
            if [ "$http_code" = "$expected_status" ]; then
                print_success "$description"
                debug "Response: $body"
                return 0
            else
                print_warning "$description (attempt $attempt/$RETRIES) - HTTP $http_code"
                debug "Response body: $body"
            fi
        else
            print_warning "$description (attempt $attempt/$RETRIES) - Connection failed"
        fi
        
        if [ $attempt -lt $RETRIES ]; then
            debug "Retrying in 2 seconds..."
            sleep 2
        fi
    done
    
    print_error "$description - Failed after $RETRIES attempts"
    return 1
}

# Specific health checks for ADHD server
check_adhd_performance() {
    local start_time=$(date +%s%3N)
    
    if check_endpoint "/health" "200" "Basic health check"; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        
        if [ $response_time -lt 3000 ]; then
            print_success "ADHD response time target met: ${response_time}ms < 3000ms"
        else
            print_warning "ADHD response time target exceeded: ${response_time}ms >= 3000ms"
            return 1
        fi
    else
        return 1
    fi
}

check_detailed_health() {
    print_status "Checking detailed health status..."
    
    local response
    if response=$(curl -s --max-time $TIMEOUT "$APP_URL/health" 2>/dev/null); then
        # Parse JSON response to check component health
        if command -v jq >/dev/null 2>&1; then
            local status=$(echo "$response" | jq -r '.status // "unknown"')
            local db_status=$(echo "$response" | jq -r '.components.database.status // "unknown"')
            local redis_status=$(echo "$response" | jq -r '.components.redis.status // "unknown"')
            local llm_status=$(echo "$response" | jq -r '.components.llm.status // "unknown"')
            
            print_status "Overall status: $status"
            print_status "Database: $db_status"
            print_status "Redis: $redis_status"
            print_status "LLM: $llm_status"
            
            if [ "$status" = "healthy" ]; then
                print_success "Detailed health check passed"
                return 0
            else
                print_warning "System status: $status"
                return 1
            fi
        else
            # Basic check without jq
            if echo "$response" | grep -q '"status":"healthy"'; then
                print_success "Detailed health check passed"
                return 0
            else
                print_warning "System not fully healthy"
                return 1
            fi
        fi
    else
        print_error "Failed to get detailed health status"
        return 1
    fi
}

check_metrics() {
    print_status "Checking metrics endpoint..."
    
    local response
    if response=$(curl -s --max-time $TIMEOUT "$APP_URL/metrics" 2>/dev/null); then
        # Check for ADHD-specific metrics
        local adhd_metrics=0
        
        if echo "$response" | grep -q "adhd_"; then
            adhd_metrics=$((adhd_metrics + 1))
        fi
        
        if echo "$response" | grep -q "cognitive_load"; then
            adhd_metrics=$((adhd_metrics + 1))
        fi
        
        if echo "$response" | grep -q "hyperfocus"; then
            adhd_metrics=$((adhd_metrics + 1))
        fi
        
        if [ $adhd_metrics -ge 2 ]; then
            print_success "ADHD metrics available ($adhd_metrics found)"
            return 0
        else
            print_warning "Limited ADHD metrics available ($adhd_metrics found)"
            return 1
        fi
    else
        print_error "Metrics endpoint not accessible"
        return 1
    fi
}

check_security_headers() {
    print_status "Checking security headers..."
    
    local headers
    if headers=$(curl -I -s --max-time $TIMEOUT "$APP_URL/health" 2>/dev/null); then
        local security_score=0
        
        # Check for essential security headers
        if echo "$headers" | grep -qi "X-Content-Type-Options: nosniff"; then
            security_score=$((security_score + 1))
        fi
        
        if echo "$headers" | grep -qi "X-Frame-Options: DENY"; then
            security_score=$((security_score + 1))
        fi
        
        if echo "$headers" | grep -qi "X-XSS-Protection"; then
            security_score=$((security_score + 1))
        fi
        
        # Check for ADHD-specific headers
        if echo "$headers" | grep -qi "X-Optimized-For: Executive-Function"; then
            security_score=$((security_score + 1))
            print_success "ADHD optimization headers present"
        fi
        
        if [ $security_score -ge 3 ]; then
            print_success "Security headers check passed ($security_score/4)"
            return 0
        else
            print_warning "Some security headers missing ($security_score/4)"
            return 1
        fi
    else
        print_error "Failed to check security headers"
        return 1
    fi
}

# Main health check execution
main() {
    print_status "Starting comprehensive health check for MCP ADHD Server"
    print_status "Target URL: $APP_URL"
    print_status "Timeout: ${TIMEOUT}s, Retries: $RETRIES"
    echo ""
    
    local checks_passed=0
    local total_checks=5
    
    # Execute all health checks
    if check_adhd_performance; then
        checks_passed=$((checks_passed + 1))
    fi
    
    if check_detailed_health; then
        checks_passed=$((checks_passed + 1))
    fi
    
    if check_endpoint "/ready" "200" "Readiness check"; then
        checks_passed=$((checks_passed + 1))
    fi
    
    if check_metrics; then
        checks_passed=$((checks_passed + 1))
    fi
    
    if check_security_headers; then
        checks_passed=$((checks_passed + 1))
    fi
    
    echo ""
    print_status "Health check results: $checks_passed/$total_checks checks passed"
    
    if [ $checks_passed -eq $total_checks ]; then
        print_success "All health checks passed! System is ready for production."
        exit 0
    elif [ $checks_passed -ge 3 ]; then
        print_warning "Most health checks passed. System is functional but may need attention."
        exit 1
    else
        print_error "Multiple health checks failed. System needs attention before production use."
        exit 2
    fi
}

# Handle command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            APP_URL="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -r|--retries)
            RETRIES="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -u, --url URL       Application URL (default: http://localhost:8000)"
            echo "  -t, --timeout SEC   Request timeout in seconds (default: 10)"
            echo "  -r, --retries NUM   Number of retries (default: 3)"
            echo "  -v, --verbose       Enable verbose output"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Exit codes:"
            echo "  0  All checks passed"
            echo "  1  Some checks failed but system is functional" 
            echo "  2  Critical failures, system needs attention"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main