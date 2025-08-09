#!/bin/bash

# Comprehensive accessibility testing script for MCP ADHD Server
# This script runs all accessibility tests and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
HEADLESS="${HEADLESS:-true}"
RESULTS_DIR="${RESULTS_DIR:-test-results}"
PYTEST_WORKERS="${PYTEST_WORKERS:-2}"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for server
wait_for_server() {
    local url="$1"
    local timeout="${2:-30}"
    local count=0
    
    print_status "Waiting for server at $url..."
    
    while [ $count -lt $timeout ]; do
        if curl -f "$url/health" >/dev/null 2>&1; then
            print_success "Server is ready at $url"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    print_error "Server not ready after ${timeout} seconds"
    return 1
}

# Function to run test suite
run_test_suite() {
    local test_file="$1"
    local test_name="$2"
    local markers="$3"
    local max_failures="${4:-5}"
    
    print_status "Running $test_name tests..."
    
    local cmd="pytest $test_file"
    
    if [ -n "$markers" ]; then
        cmd="$cmd -m '$markers'"
    fi
    
    cmd="$cmd -v --maxfail=$max_failures --tb=short"
    cmd="$cmd --html=$RESULTS_DIR/$test_name-report.html --self-contained-html"
    cmd="$cmd --junit-xml=$RESULTS_DIR/$test_name.xml"
    cmd="$cmd -n $PYTEST_WORKERS"
    
    if eval $cmd; then
        print_success "$test_name tests passed"
        return 0
    else
        print_error "$test_name tests failed"
        return 1
    fi
}

# Main function
main() {
    echo "========================================"
    echo "MCP ADHD Server Accessibility Testing"
    echo "========================================"
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! command_exists pytest; then
        print_error "pytest not found. Install with: pip install pytest"
        exit 1
    fi
    
    if ! command_exists playwright; then
        print_error "playwright not found. Install with: pip install playwright && playwright install"
        exit 1
    fi
    
    # Check if axe-playwright-python is available
    if ! python -c "import axe_playwright_python" 2>/dev/null; then
        print_warning "axe-playwright-python not available. Some tests may be skipped."
    fi
    
    # Create results directory
    mkdir -p "$RESULTS_DIR/accessibility"
    mkdir -p "$RESULTS_DIR/screenshots"
    
    print_status "Results will be saved to: $RESULTS_DIR"
    print_status "Server URL: $BASE_URL"
    print_status "Headless mode: $HEADLESS"
    
    # Check server connectivity
    if ! wait_for_server "$BASE_URL" 30; then
        print_error "Cannot connect to server. Please ensure the server is running at $BASE_URL"
        
        if [ "$BASE_URL" = "http://localhost:8000" ]; then
            print_status "To start the server, run:"
            print_status "python -m uvicorn src.mcp_server.main:app --reload --port 8000"
        fi
        
        exit 1
    fi
    
    # Export environment variables for tests
    export BASE_URL HEADLESS RESULTS_DIR
    
    # Test execution tracking
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    local test_results=()
    
    print_status "Starting accessibility test execution..."
    
    # 1. WCAG Compliance Tests (Critical)
    print_status "==================== WCAG COMPLIANCE TESTS ===================="
    total_tests=$((total_tests + 1))
    if run_test_suite "tests/accessibility/test_wcag_compliance.py" "wcag-compliance" "wcag" 3; then
        passed_tests=$((passed_tests + 1))
        test_results+=("✅ WCAG Compliance")
    else
        failed_tests=$((failed_tests + 1))
        test_results+=("❌ WCAG Compliance")
    fi
    
    # 2. ADHD-Specific Accessibility Tests (Critical)
    print_status "==================== ADHD ACCESSIBILITY TESTS =================="
    total_tests=$((total_tests + 1))
    if run_test_suite "tests/accessibility/test_adhd_accessibility.py" "adhd-accessibility" "adhd_critical" 2; then
        passed_tests=$((passed_tests + 1))
        test_results+=("✅ ADHD Accessibility")
    else
        failed_tests=$((failed_tests + 1))
        test_results+=("❌ ADHD Accessibility")
    fi
    
    # 3. Crisis Features Tests (Life-Critical)
    print_status "==================== CRISIS FEATURES TESTS ===================="
    total_tests=$((total_tests + 1))
    if run_test_suite "tests/accessibility/test_adhd_accessibility.py" "crisis-features" "crisis" 1; then
        passed_tests=$((passed_tests + 1))
        test_results+=("✅ Crisis Features")
    else
        failed_tests=$((failed_tests + 1))
        test_results+=("❌ Crisis Features")
    fi
    
    # 4. Multi-Disability Intersection Tests
    print_status "==================== MULTI-DISABILITY TESTS =================="
    total_tests=$((total_tests + 1))
    if run_test_suite "tests/accessibility/test_multi_disability.py" "multi-disability" "multi_disability" 3; then
        passed_tests=$((passed_tests + 1))
        test_results+=("✅ Multi-Disability")
    else
        failed_tests=$((failed_tests + 1))
        test_results+=("❌ Multi-Disability")
    fi
    
    # 5. Lighthouse Audits (Optional)
    if command_exists lighthouse; then
        print_status "==================== LIGHTHOUSE AUDITS ======================="
        total_tests=$((total_tests + 1))
        if run_test_suite "tests/accessibility/test_lighthouse_audit.py" "lighthouse-audit" "lighthouse" 5; then
            passed_tests=$((passed_tests + 1))
            test_results+=("✅ Lighthouse Audit")
        else
            failed_tests=$((failed_tests + 1))
            test_results+=("❌ Lighthouse Audit")
        fi
    else
        print_warning "Lighthouse not available - skipping Lighthouse audits"
        print_status "Install with: npm install -g lighthouse"
    fi
    
    # Generate comprehensive report
    print_status "==================== GENERATING REPORTS ======================"
    
    if command_exists python; then
        if python scripts/generate_accessibility_report.py --results-dir "$RESULTS_DIR/accessibility" 2>/dev/null; then
            print_success "Comprehensive accessibility report generated"
        else
            print_warning "Could not generate comprehensive report - check test results manually"
        fi
    fi
    
    # Display final results
    echo ""
    echo "========================================"
    echo "ACCESSIBILITY TEST SUMMARY"
    echo "========================================"
    
    for result in "${test_results[@]}"; do
        echo "$result"
    done
    
    echo ""
    echo "Total Test Suites: $total_tests"
    echo "Passed: $passed_tests"
    echo "Failed: $failed_tests"
    echo ""
    
    # Check for critical failures
    local critical_failures=0
    
    if [[ " ${test_results[*]} " =~ "❌ WCAG Compliance" ]]; then
        print_error "CRITICAL: WCAG compliance tests failed"
        critical_failures=$((critical_failures + 1))
    fi
    
    if [[ " ${test_results[*]} " =~ "❌ Crisis Features" ]]; then
        print_error "CRITICAL: Crisis features accessibility tests failed (LIFE-CRITICAL)"
        critical_failures=$((critical_failures + 1))
    fi
    
    if [[ " ${test_results[*]} " =~ "❌ ADHD Accessibility" ]]; then
        print_error "CRITICAL: ADHD accessibility tests failed"
        critical_failures=$((critical_failures + 1))
    fi
    
    # Final status
    if [ $failed_tests -eq 0 ]; then
        print_success "All accessibility tests passed! ✅"
        echo ""
        print_status "The MCP ADHD Server meets all accessibility requirements:"
        print_status "✅ WCAG 2.1 AA compliant"
        print_status "✅ ADHD-friendly design"
        print_status "✅ Multi-disability support"
        print_status "✅ Crisis features fully accessible"
        echo ""
        print_status "View detailed reports in: $RESULTS_DIR/"
        exit 0
    elif [ $critical_failures -gt 0 ]; then
        print_error "CRITICAL accessibility failures detected!"
        echo ""
        print_error "The following issues must be resolved immediately:"
        
        if [[ " ${test_results[*]} " =~ "❌ Crisis Features" ]]; then
            print_error "• Crisis features not accessible (life-critical issue)"
        fi
        
        if [[ " ${test_results[*]} " =~ "❌ WCAG Compliance" ]]; then
            print_error "• WCAG 2.1 AA compliance violations"
        fi
        
        if [[ " ${test_results[*]} " =~ "❌ ADHD Accessibility" ]]; then
            print_error "• ADHD-specific accessibility failures"
        fi
        
        echo ""
        print_error "These failures affect users' ability to access critical functionality."
        print_status "Review detailed reports in: $RESULTS_DIR/"
        exit 1
    else
        print_warning "Some accessibility tests failed, but no critical issues detected"
        echo ""
        print_status "Non-critical issues found - review and fix when possible:"
        
        for result in "${test_results[@]}"; do
            if [[ "$result" =~ "❌" ]]; then
                print_warning "• ${result#❌ }"
            fi
        done
        
        echo ""
        print_status "View detailed reports in: $RESULTS_DIR/"
        exit 2
    fi
}

# Help function
show_help() {
    cat << EOF
MCP ADHD Server Accessibility Testing Script

Usage: $0 [OPTIONS]

Options:
  -h, --help              Show this help message
  -u, --url URL          Set base URL (default: http://localhost:8000)
  -d, --results-dir DIR   Set results directory (default: test-results)
  -w, --workers NUM       Set number of pytest workers (default: 2)
  --headless BOOL         Set headless mode (default: true)
  --no-server-check       Skip server connectivity check

Environment Variables:
  BASE_URL               Server URL for testing
  HEADLESS               Run browsers in headless mode (true/false)
  RESULTS_DIR            Directory for test results
  PYTEST_WORKERS         Number of parallel test workers

Examples:
  $0                                    # Run with defaults
  $0 --url http://localhost:3000       # Test different server
  $0 --results-dir my-results          # Custom results directory
  $0 --workers 4                       # Use 4 parallel workers
  HEADLESS=false $0                     # Run with visible browsers

Test Suites:
  1. WCAG 2.1 AA Compliance Tests      (Critical)
  2. ADHD-Specific Accessibility Tests (Critical)
  3. Crisis Features Tests             (Life-Critical)
  4. Multi-Disability Tests            (Important)
  5. Lighthouse Audits                 (Optional)

Exit Codes:
  0: All tests passed
  1: Critical failures detected
  2: Non-critical failures detected
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -d|--results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        -w|--workers)
            PYTEST_WORKERS="$2"
            shift 2
            ;;
        --headless)
            HEADLESS="$2"
            shift 2
            ;;
        --no-server-check)
            SKIP_SERVER_CHECK=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            print_status "Use $0 --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"