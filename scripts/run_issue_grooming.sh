#!/bin/bash

# GitHub Issue Grooming Runner for ADHDo Project
# 
# This script provides easy access to the GitHub issue grooming agent
# with different modes of operation.

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GROOMING_SCRIPT="$SCRIPT_DIR/github_issue_grooming.py"
REPORT_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}🤖 GitHub Issue Grooming Agent${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check dependencies
check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "Git is required but not installed."
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir &> /dev/null; then
        print_error "Not in a git repository."
        exit 1
    fi
    
    # Create reports directory if it doesn't exist
    mkdir -p "$REPORT_DIR"
    
    print_success "Dependencies check passed"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    # Check if requests is available
    if ! python3 -c "import requests" &> /dev/null; then
        print_warning "Installing required Python packages..."
        pip3 install requests structlog --user
    fi
    
    print_success "Python dependencies ready"
}

# Show usage information
show_usage() {
    print_header
    echo
    echo "Usage: $0 [MODE] [OPTIONS]"
    echo
    echo "MODES:"
    echo "  analyze     - Generate analysis report only (default)"
    echo "  interactive - Interactive mode for reviewing recommendations"
    echo "  auto        - Automatically execute safe recommendations"
    echo "  dry-run     - Show what would be done without making changes"
    echo "  help        - Show this help message"
    echo
    echo "OPTIONS:"
    echo "  --token TOKEN    - GitHub personal access token"
    echo "  --output FILE    - Output file for report (default: timestamped)"
    echo "  --verbose        - Enable verbose logging"
    echo
    echo "EXAMPLES:"
    echo "  $0 analyze"
    echo "  $0 interactive --token \$GITHUB_TOKEN"
    echo "  $0 auto --token \$GITHUB_TOKEN"
    echo "  $0 dry-run --output custom_report.md"
    echo
    echo "ENVIRONMENT VARIABLES:"
    echo "  GITHUB_TOKEN     - GitHub personal access token"
    echo
}

# Run analysis mode
run_analyze() {
    local output_file="$1"
    print_info "Running issue analysis..."
    
    python3 "$GROOMING_SCRIPT" \
        --analyze-only \
        --output "$output_file" \
        ${GITHUB_TOKEN:+--github-token "$GITHUB_TOKEN"}
    
    print_success "Analysis complete!"
    print_info "Report saved to: $output_file"
    
    # Show summary if file exists
    if [[ -f "$output_file" ]]; then
        echo
        print_info "Report Summary:"
        echo "$(head -n 20 "$output_file")"
        echo
        print_info "View full report: cat $output_file"
    fi
}

# Run interactive mode
run_interactive() {
    local output_file="$1"
    print_info "Starting interactive mode..."
    
    if [[ -z "$GITHUB_TOKEN" ]]; then
        print_warning "No GitHub token provided. Some features may be limited."
        print_info "Set GITHUB_TOKEN environment variable or use --token option"
    fi
    
    python3 "$GROOMING_SCRIPT" \
        --interactive \
        --output "$output_file" \
        ${GITHUB_TOKEN:+--github-token "$GITHUB_TOKEN"}
}

# Run auto-update mode
run_auto() {
    local output_file="$1"
    print_info "Running auto-update mode..."
    
    if [[ -z "$GITHUB_TOKEN" ]]; then
        print_error "GitHub token required for auto-update mode"
        print_info "Set GITHUB_TOKEN environment variable or use --token option"
        exit 1
    fi
    
    python3 "$GROOMING_SCRIPT" \
        --auto-update \
        --output "$output_file" \
        --github-token "$GITHUB_TOKEN"
    
    print_success "Auto-update complete!"
}

# Run dry-run mode
run_dry_run() {
    local output_file="$1"
    print_info "Running dry-run analysis..."
    
    # First generate the report
    python3 "$GROOMING_SCRIPT" \
        --analyze-only \
        --output "$output_file" \
        ${GITHUB_TOKEN:+--github-token "$GITHUB_TOKEN"}
    
    print_success "Dry-run analysis complete!"
    print_info "This shows what WOULD be done without making actual changes"
    
    # Show the recommendations
    if [[ -f "$output_file" ]]; then
        echo
        print_info "Recommendations Preview:"
        echo "$(grep -A 5 "## 🎯 Immediate Action Items" "$output_file" || echo "No action items found")"
    fi
}

# Main execution
main() {
    # Parse arguments
    MODE="analyze"
    OUTPUT_FILE=""
    VERBOSE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            analyze|interactive|auto|dry-run|help)
                MODE="$1"
                shift
                ;;
            --token)
                GITHUB_TOKEN="$2"
                shift 2
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Show help if requested
    if [[ "$MODE" == "help" ]]; then
        show_usage
        exit 0
    fi
    
    # Set default output file if not specified
    if [[ -z "$OUTPUT_FILE" ]]; then
        OUTPUT_FILE="$REPORT_DIR/issue_grooming_report_$TIMESTAMP.md"
    fi
    
    # Enable verbose mode if requested
    if [[ "$VERBOSE" == true ]]; then
        set -x
    fi
    
    print_header
    
    # Check dependencies
    check_dependencies
    install_dependencies
    
    # Print configuration
    print_info "Configuration:"
    echo "  Mode: $MODE"
    echo "  Output: $OUTPUT_FILE"
    echo "  GitHub Token: ${GITHUB_TOKEN:+[SET]}${GITHUB_TOKEN:-[NOT SET]}"
    echo
    
    # Execute based on mode
    case "$MODE" in
        analyze)
            run_analyze "$OUTPUT_FILE"
            ;;
        interactive)
            run_interactive "$OUTPUT_FILE"
            ;;
        auto)
            run_auto "$OUTPUT_FILE"
            ;;
        dry-run)
            run_dry_run "$OUTPUT_FILE"
            ;;
        *)
            print_error "Unknown mode: $MODE"
            show_usage
            exit 1
            ;;
    esac
    
    echo
    print_success "Issue grooming completed successfully!"
    
    # Suggest next steps
    case "$MODE" in
        analyze|dry-run)
            print_info "Next steps:"
            echo "  1. Review the report: cat $OUTPUT_FILE"
            echo "  2. Run interactive mode: $0 interactive"
            echo "  3. Auto-execute safe actions: $0 auto --token \$GITHUB_TOKEN"
            ;;
        interactive|auto)
            print_info "Consider scheduling regular grooming:"
            echo "  - Weekly analysis: $0 analyze"
            echo "  - Monthly cleanup: $0 auto --token \$GITHUB_TOKEN"
            ;;
    esac
}

# Execute main function with all arguments
main "$@"