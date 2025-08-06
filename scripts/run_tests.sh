#!/bin/bash
# MCP ADHD Server - Test Runner Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Test categories
run_unit_tests() {
    print_status "Running unit tests..."
    poetry run pytest tests/unit \
        --cov=src/mcp_server \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        --junit-xml=test-results/unit-results.xml \
        -v --tb=short --maxfail=10
    print_success "Unit tests completed"
}

run_integration_tests() {
    print_status "Running integration tests..."
    poetry run pytest tests/integration \
        --junit-xml=test-results/integration-results.xml \
        -v --tb=short --maxfail=5
    print_success "Integration tests completed"
}

run_performance_tests() {
    print_status "Running performance and ADHD-specific tests..."
    poetry run pytest tests/performance \
        --junit-xml=test-results/performance-results.xml \
        -v --tb=short --maxfail=5 \
        -m "performance or adhd"
    print_success "Performance tests completed"
}

run_adhd_tests() {
    print_status "Running ADHD-specific tests across all categories..."
    poetry run pytest \
        --junit-xml=test-results/adhd-results.xml \
        -v --tb=short -m "adhd"
    print_success "ADHD tests completed"
}

run_all_tests() {
    print_status "Running complete test suite..."
    mkdir -p test-results
    
    run_unit_tests
    run_integration_tests
    run_performance_tests
    
    print_success "All tests completed successfully!"
    
    if [ -f "coverage.xml" ]; then
        print_status "Coverage report: coverage_html_report/index.html"
    fi
}

show_help() {
    echo "MCP ADHD Server Test Runner"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  unit          Run unit tests only"
    echo "  integration   Run integration tests only" 
    echo "  performance   Run performance and ADHD tests"
    echo "  adhd          Run all ADHD-specific tests"
    echo "  all           Run complete test suite (default)"
    echo "  help          Show this help message"
    echo ""
    echo "ADHD-Optimized Testing:"
    echo "  • Response time validation (<3s target)"
    echo "  • Cognitive load calculation accuracy" 
    echo "  • Pattern recognition for ADHD states"
    echo "  • Crisis intervention scenarios"
}

# Main execution
case "${1:-all}" in
    "unit") mkdir -p test-results && run_unit_tests ;;
    "integration") mkdir -p test-results && run_integration_tests ;;
    "performance") mkdir -p test-results && run_performance_tests ;;
    "adhd") mkdir -p test-results && run_adhd_tests ;;
    "all") run_all_tests ;;
    "help"|"-h"|"--help") show_help ;;
    *) print_error "Unknown command: $1"; echo ""; show_help; exit 1 ;;
esac