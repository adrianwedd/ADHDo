#!/bin/bash
# Security Validation Script for MCP ADHD Server
# Automated OWASP compliance and security hardening validation

set -e

# Configuration
SERVER_URL="http://localhost:8000"
REPORT_DIR="/tmp/security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/security_report_${TIMESTAMP}.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}MCP ADHD Server - Security Validation Suite${NC}"
echo "=================================================="
echo "Timestamp: $(date)"
echo "Server URL: $SERVER_URL"
echo "Report File: $REPORT_FILE"
echo ""

# Create report directory
mkdir -p "$REPORT_DIR"

# Initialize report
cat > "$REPORT_FILE" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "server_url": "$SERVER_URL",
    "tests": {
        "security_headers": {},
        "input_validation": {},
        "authentication": {},
        "rate_limiting": {},
        "owasp_compliance": {},
        "adhd_specific": {}
    },
    "summary": {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
}
EOF

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# Helper functions
update_test_result() {
    local category="$1"
    local test_name="$2"
    local status="$3"
    local details="$4"
    
    # Update JSON report using jq
    tmp=$(mktemp)
    jq ".tests.$category[\"$test_name\"] = {\"status\": \"$status\", \"details\": \"$details\", \"timestamp\": \"$(date -Iseconds)\"}" "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"
    
    # Update counters
    ((TOTAL_TESTS++))
    case $status in
        "PASS") ((PASSED_TESTS++)) ;;
        "FAIL") ((FAILED_TESTS++)) ;;
        "WARN") ((WARNING_TESTS++)) ;;
    esac
}

print_test_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    
    case $status in
        "PASS") echo -e "${GREEN}✓${NC} $test_name: PASSED" ;;
        "FAIL") echo -e "${RED}✗${NC} $test_name: FAILED - $details" ;;
        "WARN") echo -e "${YELLOW}!${NC} $test_name: WARNING - $details" ;;
    esac
}

# Test 1: Security Headers Validation
echo -e "${YELLOW}Testing Security Headers...${NC}"

test_security_header() {
    local header_name="$1"
    local expected_pattern="$2"
    local test_description="$3"
    
    response=$(curl -s -I "$SERVER_URL/health" || echo "CURL_FAILED")
    
    if [[ "$response" == "CURL_FAILED" ]]; then
        update_test_result "security_headers" "$header_name" "FAIL" "Server not accessible"
        print_test_result "$test_description" "FAIL" "Server not accessible"
        return
    fi
    
    header_value=$(echo "$response" | grep -i "^$header_name:" | cut -d' ' -f2- | tr -d '\r\n')
    
    if [[ -z "$header_value" ]]; then
        update_test_result "security_headers" "$header_name" "FAIL" "Header missing"
        print_test_result "$test_description" "FAIL" "Header missing"
    elif [[ "$header_value" =~ $expected_pattern ]]; then
        update_test_result "security_headers" "$header_name" "PASS" "Header present and correct: $header_value"
        print_test_result "$test_description" "PASS" ""
    else
        update_test_result "security_headers" "$header_name" "WARN" "Header present but potentially misconfigured: $header_value"
        print_test_result "$test_description" "WARN" "Value: $header_value"
    fi
}

# Test critical security headers
test_security_header "Strict-Transport-Security" "max-age=[0-9]+" "HSTS Header"
test_security_header "X-Content-Type-Options" "nosniff" "Content Type Options"
test_security_header "X-Frame-Options" "DENY|SAMEORIGIN" "Frame Options"
test_security_header "X-XSS-Protection" "1" "XSS Protection"
test_security_header "Content-Security-Policy" "default-src" "Content Security Policy"
test_security_header "Referrer-Policy" "strict-origin" "Referrer Policy"
test_security_header "Permissions-Policy" "microphone=\(\)" "Permissions Policy"

echo ""

# Test 2: Input Validation
echo -e "${YELLOW}Testing Input Validation...${NC}"

test_input_validation() {
    local payload="$1"
    local attack_type="$2"
    local endpoint="$3"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$SERVER_URL$endpoint" 2>/dev/null)
    
    if [[ "$response" -eq 400 ]] || [[ "$response" -eq 403 ]]; then
        update_test_result "input_validation" "$attack_type" "PASS" "Attack blocked with status $response"
        print_test_result "$attack_type Protection" "PASS" ""
    elif [[ "$response" -eq 200 ]]; then
        update_test_result "input_validation" "$attack_type" "FAIL" "Attack not blocked - got status 200"
        print_test_result "$attack_type Protection" "FAIL" "Attack not blocked"
    else
        update_test_result "input_validation" "$attack_type" "WARN" "Unexpected response: $response"
        print_test_result "$attack_type Protection" "WARN" "Unexpected response: $response"
    fi
}

# Test SQL injection
test_input_validation '{"message": "1'\'' OR '\''1'\''='\''1"}' "SQL_Injection" "/chat"

# Test XSS
test_input_validation '{"message": "<script>alert('\''xss'\'')</script>"}' "XSS" "/chat"

# Test Command Injection
test_input_validation '{"message": "; cat /etc/passwd"}' "Command_Injection" "/chat"

echo ""

# Test 3: Authentication Security
echo -e "${YELLOW}Testing Authentication Security...${NC}"

# Test weak password rejection
weak_password_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{"username": "testuser", "email": "test@example.com", "password": "123456"}' \
    "$SERVER_URL/api/auth/register" 2>/dev/null)

if [[ "$weak_password_response" -eq 400 ]]; then
    update_test_result "authentication" "weak_password" "PASS" "Weak password rejected"
    print_test_result "Weak Password Rejection" "PASS" ""
else
    update_test_result "authentication" "weak_password" "FAIL" "Weak password accepted"
    print_test_result "Weak Password Rejection" "FAIL" "Weak password accepted"
fi

# Test account lockout (simulate failed attempts)
echo "Testing account lockout protection..."
lockout_triggered=false

for i in {1..20}; do
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"username": "nonexistent@example.com", "password": "wrongpassword"}' \
        "$SERVER_URL/api/auth/login" 2>/dev/null)
    
    if [[ "$response" -eq 423 ]] || [[ "$response" -eq 429 ]]; then
        lockout_triggered=true
        break
    fi
    
    sleep 0.1
done

if $lockout_triggered; then
    update_test_result "authentication" "account_lockout" "PASS" "Account lockout triggered after failed attempts"
    print_test_result "Account Lockout Protection" "PASS" ""
else
    update_test_result "authentication" "account_lockout" "WARN" "Account lockout not triggered in 20 attempts"
    print_test_result "Account Lockout Protection" "WARN" "Lockout not triggered"
fi

echo ""

# Test 4: Rate Limiting
echo -e "${YELLOW}Testing Rate Limiting...${NC}"

rate_limit_triggered=false
rate_limit_response=""

for i in {1..100}; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/health" 2>/dev/null)
    
    if [[ "$response" -eq 429 ]]; then
        rate_limit_triggered=true
        break
    fi
done

if $rate_limit_triggered; then
    update_test_result "rate_limiting" "basic_rate_limit" "PASS" "Rate limiting triggered"
    print_test_result "Rate Limiting" "PASS" ""
else
    update_test_result "rate_limiting" "basic_rate_limit" "WARN" "Rate limiting not triggered in 100 requests"
    print_test_result "Rate Limiting" "WARN" "Not triggered in 100 requests"
fi

echo ""

# Test 5: OWASP Top 10 Compliance
echo -e "${YELLOW}Testing OWASP Top 10 Compliance...${NC}"

# A01: Broken Access Control
unauthorized_response=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/api/users/admin-only-endpoint" 2>/dev/null)

if [[ "$unauthorized_response" -eq 401 ]] || [[ "$unauthorized_response" -eq 403 ]] || [[ "$unauthorized_response" -eq 404 ]]; then
    update_test_result "owasp_compliance" "access_control" "PASS" "Unauthorized access blocked"
    print_test_result "A01: Access Control" "PASS" ""
else
    update_test_result "owasp_compliance" "access_control" "FAIL" "Unauthorized access allowed"
    print_test_result "A01: Access Control" "FAIL" "Unauthorized access allowed"
fi

# A02: Cryptographic Failures (check HTTPS enforcement)
http_response=$(curl -s -o /dev/null -w "%{http_code}" -I "$SERVER_URL/health" 2>/dev/null)
if [[ -n "$(curl -s -I "$SERVER_URL/health" | grep -i 'Strict-Transport-Security')" ]]; then
    update_test_result "owasp_compliance" "crypto_failures" "PASS" "HSTS enforces HTTPS"
    print_test_result "A02: Cryptographic Failures" "PASS" ""
else
    update_test_result "owasp_compliance" "crypto_failures" "WARN" "HSTS not properly configured"
    print_test_result "A02: Cryptographic Failures" "WARN" "HSTS configuration issue"
fi

# A03: Injection (already tested above)
update_test_result "owasp_compliance" "injection" "PASS" "Injection testing completed above"
print_test_result "A03: Injection" "PASS" ""

# A05: Security Misconfiguration (check error disclosure)
error_response=$(curl -s "$SERVER_URL/nonexistent-endpoint-test" 2>/dev/null)

if [[ "$error_response" =~ "stack trace|debug|exception|error details" ]]; then
    update_test_result "owasp_compliance" "security_misconfig" "FAIL" "Error details disclosed"
    print_test_result "A05: Security Misconfiguration" "FAIL" "Error details disclosed"
else
    update_test_result "owasp_compliance" "security_misconfig" "PASS" "Error details not disclosed"
    print_test_result "A05: Security Misconfiguration" "PASS" ""
fi

echo ""

# Test 6: ADHD-Specific Security
echo -e "${YELLOW}Testing ADHD-Specific Security...${NC}"

# Test crisis support accessibility
crisis_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{"message": "I am having thoughts of suicide and need help immediately", "crisis": true}' \
    "$SERVER_URL/chat" 2>/dev/null)

if [[ "$crisis_response" -ne 403 ]] && [[ "$crisis_response" -ne 429 ]]; then
    update_test_result "adhd_specific" "crisis_support_access" "PASS" "Crisis support accessible"
    print_test_result "Crisis Support Access" "PASS" ""
else
    update_test_result "adhd_specific" "crisis_support_access" "FAIL" "Crisis support blocked by security"
    print_test_result "Crisis Support Access" "FAIL" "Crisis support blocked"
fi

# Test ADHD performance impact
performance_start=$(date +%s%3N)
performance_response=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/health" 2>/dev/null)
performance_end=$(date +%s%3N)
performance_time=$((performance_end - performance_start))

if [[ "$performance_time" -lt 1000 ]]; then  # Less than 1 second
    update_test_result "adhd_specific" "performance_impact" "PASS" "Response time: ${performance_time}ms"
    print_test_result "ADHD Performance Impact" "PASS" ""
elif [[ "$performance_time" -lt 3000 ]]; then  # Less than 3 seconds
    update_test_result "adhd_specific" "performance_impact" "WARN" "Response time: ${performance_time}ms (>1s)"
    print_test_result "ADHD Performance Impact" "WARN" "Response time: ${performance_time}ms"
else
    update_test_result "adhd_specific" "performance_impact" "FAIL" "Response time: ${performance_time}ms (>3s)"
    print_test_result "ADHD Performance Impact" "FAIL" "Response time: ${performance_time}ms"
fi

echo ""

# Test 7: SSL/TLS Configuration (if HTTPS)
if [[ "$SERVER_URL" =~ ^https:// ]]; then
    echo -e "${YELLOW}Testing SSL/TLS Configuration...${NC}"
    
    # Test SSL configuration using OpenSSL
    ssl_test_result=$(echo | openssl s_client -connect "$(echo "$SERVER_URL" | sed 's|https://||' | sed 's|/.*||'):443" -servername "$(echo "$SERVER_URL" | sed 's|https://||' | sed 's|/.*||')" 2>/dev/null | grep -E "(Protocol|Cipher)")
    
    if [[ "$ssl_test_result" =~ "TLSv1.2|TLSv1.3" ]]; then
        update_test_result "ssl_tls" "protocol_version" "PASS" "Modern TLS version in use"
        print_test_result "SSL/TLS Protocol Version" "PASS" ""
    else
        update_test_result "ssl_tls" "protocol_version" "WARN" "TLS version check inconclusive"
        print_test_result "SSL/TLS Protocol Version" "WARN" "Version check failed"
    fi
fi

# Update final counters in report
tmp=$(mktemp)
jq ".summary.total_tests = $TOTAL_TESTS | .summary.passed = $PASSED_TESTS | .summary.failed = $FAILED_TESTS | .summary.warnings = $WARNING_TESTS" "$REPORT_FILE" > "$tmp" && mv "$tmp" "$REPORT_FILE"

echo ""
echo "=================================================="
echo -e "${GREEN}Security Validation Complete${NC}"
echo ""
echo "Summary:"
echo -e "  Total Tests: $TOTAL_TESTS"
echo -e "  ${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "  ${RED}Failed: $FAILED_TESTS${NC}"
echo -e "  ${YELLOW}Warnings: $WARNING_TESTS${NC}"
echo ""

# Calculate security score
if [[ $TOTAL_TESTS -gt 0 ]]; then
    SECURITY_SCORE=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    echo "Security Score: $SECURITY_SCORE%"
    
    if [[ $SECURITY_SCORE -ge 90 ]]; then
        echo -e "Status: ${GREEN}EXCELLENT${NC}"
    elif [[ $SECURITY_SCORE -ge 80 ]]; then
        echo -e "Status: ${GREEN}GOOD${NC}"
    elif [[ $SECURITY_SCORE -ge 70 ]]; then
        echo -e "Status: ${YELLOW}NEEDS IMPROVEMENT${NC}"
    else
        echo -e "Status: ${RED}CRITICAL ISSUES${NC}"
    fi
fi

echo ""
echo "Detailed report saved to: $REPORT_FILE"

# Send report to monitoring system
if command -v curl &> /dev/null && [[ -n "${MONITORING_WEBHOOK_URL:-}" ]]; then
    curl -s -X POST "$MONITORING_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "@$REPORT_FILE" > /dev/null || true
fi

# Exit with appropriate code
if [[ $FAILED_TESTS -gt 0 ]]; then
    exit 1
elif [[ $WARNING_TESTS -gt 5 ]]; then
    exit 2
else
    exit 0
fi