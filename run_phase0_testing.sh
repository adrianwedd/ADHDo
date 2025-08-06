#!/bin/bash

# MCP ADHD Server - Phase 0 Beta Testing Runner
# Comprehensive automated testing before human beta users

set -e  # Exit on any error

# Configuration
SERVER_PORT=8000
SERVER_URL="http://localhost:$SERVER_PORT"
TEST_DIR="tests/playwright"
RESULTS_DIR="test-results/phase0"
LOG_FILE="$RESULTS_DIR/phase0-testing.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}$(echo "$1" | sed 's/./=/g')${NC}"
}

print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        print_info "Stopped development server (PID: $SERVER_PID)"
    fi
}

# Set up cleanup on exit
trap cleanup EXIT

print_header "🧠⚡ MCP ADHD SERVER - PHASE 0 BETA TESTING"
echo "Automated testing to validate system readiness for human beta users"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Check if server is already running
if curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
    print_warning "Server already running at $SERVER_URL"
    SERVER_RUNNING=true
else
    SERVER_RUNNING=false
fi

# Start server if not running
if [ "$SERVER_RUNNING" = false ]; then
    print_info "Starting development server..."
    
    # Check if virtual environment exists
    if [ -d "venv_beta" ]; then
        print_info "Using beta virtual environment"
        PYTHON_CMD="venv_beta/bin/python"
        PIP_CMD="venv_beta/bin/pip"
    elif [ -d "venv" ]; then
        print_info "Using virtual environment"
        PYTHON_CMD="venv/bin/python"
        PIP_CMD="venv/bin/pip"
    else
        print_warning "No virtual environment found, using system Python"
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    fi
    
    # Start server in background
    cd src
    PYTHONPATH=. ../$PYTHON_CMD -m uvicorn mcp_server.main:app --host 0.0.0.0 --port $SERVER_PORT --reload > "../$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    cd ..
    
    print_info "Server started with PID: $SERVER_PID"
    print_info "Waiting for server to be ready..."
    
    # Wait for server to be ready
    for i in {1..30}; do
        if curl -s "$SERVER_URL/health" > /dev/null 2>&1; then
            print_success "Server is ready!"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            print_error "Server failed to start within 30 seconds"
            print_error "Check log file: $LOG_FILE"
            exit 1
        fi
    done
fi

# Verify server health
print_info "Checking server health..."
HEALTH_RESPONSE=$(curl -s "$SERVER_URL/health" || echo "")

if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    print_success "Server health check passed"
else
    print_error "Server health check failed"
    print_error "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Install Playwright dependencies if needed
print_info "Setting up Playwright testing environment..."

# Check if Playwright is installed
if ! $PIP_CMD show playwright > /dev/null 2>&1; then
    print_info "Installing Playwright dependencies..."
    $PIP_CMD install playwright pytest-playwright
    
    # Install Playwright browsers
    print_info "Installing Playwright browsers..."
    $PYTHON_CMD -m playwright install chromium
else
    print_success "Playwright already installed"
fi

# Run Phase 0 beta tests
print_header "🧪 Running Phase 0 Beta Tests"
echo "Testing all ADHD-critical functionality before human users..."
echo ""

# Set environment variables for testing
export BASE_URL="$SERVER_URL"
export HEADLESS="false"  # Show browser for visual validation
export PYTEST_CURRENT_TEST=""

# Run the comprehensive beta test
START_TIME=$(date +%s)
TEST_SUCCESS=false

if ../$PYTHON_CMD "$TEST_DIR/phase0_beta_testing.py" 2>&1 | tee "$RESULTS_DIR/test-output.log"; then
    TEST_SUCCESS=true
    print_success "Phase 0 beta testing completed successfully!"
else
    print_error "Phase 0 beta testing found critical issues"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Generate summary report
print_header "📊 Phase 0 Beta Testing Summary"

echo "🕒 Test Duration: ${DURATION} seconds"
echo "🌐 Server URL: $SERVER_URL"
echo "📁 Results Directory: $RESULTS_DIR"
echo "📋 Detailed Log: $LOG_FILE"
echo ""

if [ "$TEST_SUCCESS" = true ]; then
    echo -e "${GREEN}${BOLD}🎉 BETA TESTING SUCCESS!${NC}"
    echo ""
    echo "✅ System is ready for Phase 1 beta testing with real users"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Deploy to staging environment"
    echo "   2. Recruit 10-20 ADHD beta users"
    echo "   3. Set up user feedback collection system"
    echo "   4. Monitor ADHD-specific metrics in production"
    echo "   5. Begin Phase 1 human beta testing"
    echo ""
    echo "🎯 Ready to help ADHD minds get their shit done!"
    
    # Update GitHub issues for successful Phase 0
    if command -v gh > /dev/null 2>&1; then
        print_info "Updating GitHub issues..."
        
        # Close Phase 0 related issues or add comments
        gh issue comment 13 --body "✅ Phase 0 Beta Testing Complete - User authentication system tested and ready for beta users" 2>/dev/null || true
        gh issue comment 14 --body "✅ Phase 0 Beta Testing Complete - Web interface tested and ready for beta users" 2>/dev/null || true
        gh issue comment 15 --body "✅ Phase 0 Beta Testing Complete - Telegram bot integration tested and ready for beta users" 2>/dev/null || true
        gh issue comment 16 --body "✅ Phase 0 Beta Testing Complete - API documentation validated and ready for developers" 2>/dev/null || true
        gh issue comment 17 --body "✅ Phase 0 Beta Testing Complete - Onboarding system tested and ready for ADHD users" 2>/dev/null || true
        
        print_success "GitHub issues updated with Phase 0 completion status"
    fi
    
    exit 0
else
    echo -e "${RED}${BOLD}⚠️ BETA TESTING ISSUES FOUND${NC}"
    echo ""
    echo "❌ Critical issues must be resolved before human beta testing"
    echo ""
    echo "📋 Required Actions:"
    echo "   1. Review test output above for specific failures"
    echo "   2. Fix critical ADHD-related issues"
    echo "   3. Address performance problems (must be <3s)"
    echo "   4. Improve user experience issues"
    echo "   5. Re-run Phase 0 testing until all tests pass"
    echo ""
    echo "📁 Check detailed logs in: $RESULTS_DIR/"
    
    exit 1
fi