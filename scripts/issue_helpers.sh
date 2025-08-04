#!/bin/bash
# GitHub Issue Management Helpers for ADHDo/MCP Development
# Makes it easy for agents and developers to manage project issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to create a new feature issue
create_feature_issue() {
    local title="$1"
    local description="$2"
    local labels="${3:-enhancement,phase-1}"
    
    gh issue create \
        --title "$title" \
        --body "## 🚀 Feature Request

**Description**: $description

### Requirements
- [ ] Define technical requirements
- [ ] Design implementation approach
- [ ] Write tests
- [ ] Implement feature
- [ ] Update documentation

### Acceptance Criteria
- [ ] Feature works as described
- [ ] Tests pass
- [ ] Performance impact assessed
- [ ] Documentation updated

**Created by**: Issue helper script" \
        --label "$labels"
}

# Function to create a bug report
create_bug_issue() {
    local title="$1"
    local description="$2"
    local reproduction_steps="$3"
    local labels="${4:-bug}"
    
    gh issue create \
        --title "🐛 $title" \
        --body "## Bug Report

**Description**: $description

### Reproduction Steps
$reproduction_steps

### Expected Behavior
[Describe what should happen]

### Actual Behavior  
[Describe what actually happens]

### Environment
- OS: [e.g., macOS, Linux, Windows]
- Python version: [e.g., 3.12]
- ADHDo version: [e.g., main branch]

### Additional Context
[Any other context about the problem]

**Created by**: Issue helper script" \
        --label "$labels"
}

# Function to create a performance issue
create_performance_issue() {
    local title="$1"
    local current_performance="$2"
    local target_performance="$3"
    local labels="${4:-performance,phase-1}"
    
    gh issue create \
        --title "⚡ $title" \
        --body "## Performance Optimization

**Current Performance**: $current_performance
**Target Performance**: $target_performance

### Profiling Results
- [ ] Profile current implementation
- [ ] Identify bottlenecks
- [ ] Measure baseline metrics

### Optimization Strategy
- [ ] Database query optimization
- [ ] Caching improvements  
- [ ] Algorithm improvements
- [ ] Infrastructure scaling

### Success Metrics
- [ ] Achieve target performance
- [ ] Maintain accuracy/quality
- [ ] No regression in other areas

**Created by**: Issue helper script" \
        --label "$labels"
}

# Function to create a domain expansion issue
create_domain_issue() {
    local domain_name="$1"
    local target_population="$2"
    local labels="${3:-domain-expansion,phase-2}"
    
    gh issue create \
        --title "🌍 Implement $domain_name domain" \
        --body "## New MCP Domain Implementation

**Domain**: $domain_name
**Target Population**: $target_population

### Domain Configuration
- [ ] Define crisis patterns specific to $domain_name
- [ ] Identify context types needed
- [ ] Configure cognitive load limits
- [ ] Design safety protocols

### Technical Implementation
- [ ] Create domain configuration file
- [ ] Implement domain-specific context builders
- [ ] Add crisis detection patterns
- [ ] Create domain-specific LLM prompts
- [ ] Build domain adapter

### Validation & Testing
- [ ] User research and interviews
- [ ] Prototype testing
- [ ] Clinical validation (if applicable)
- [ ] Performance benchmarking

### Go-to-Market
- [ ] Pricing strategy
- [ ] Marketing materials
- [ ] User onboarding flow
- [ ] Professional partnership channels

**Created by**: Issue helper script" \
        --label "$labels"
}

# Function to list issues by label
list_issues_by_label() {
    local label="$1"
    print_info "Issues labeled '$label':"
    gh issue list --label "$label" --state all
}

# Function to show project status dashboard
show_project_status() {
    echo -e "${BLUE}📊 ADHDo Project Status Dashboard${NC}"
    echo "=================================="
    
    print_info "Phase 1 Issues:"
    gh issue list --label "phase-1" --limit 10
    
    echo ""
    print_info "Phase 2 Issues:"
    gh issue list --label "phase-2" --limit 5
    
    echo ""
    print_info "Open Bugs:"
    gh issue list --label "bug" --state open --limit 5
    
    echo ""
    print_info "Performance Issues:"
    gh issue list --label "performance" --limit 5
}

# Function to create milestone from current todos
sync_todos_to_issues() {
    print_info "This would sync current todo list to GitHub issues"
    print_warning "Manual implementation needed - requires reading current todo state"
}

# Main command dispatcher
case "$1" in
    "feature")
        if [[ $# -lt 3 ]]; then
            print_error "Usage: $0 feature 'Title' 'Description' [labels]"
            exit 1
        fi
        create_feature_issue "$2" "$3" "$4"
        print_status "Feature issue created!"
        ;;
    "bug")
        if [[ $# -lt 4 ]]; then
            print_error "Usage: $0 bug 'Title' 'Description' 'Reproduction Steps' [labels]"
            exit 1
        fi
        create_bug_issue "$2" "$3" "$4" "$5"
        print_status "Bug issue created!"
        ;;
    "performance")
        if [[ $# -lt 4 ]]; then
            print_error "Usage: $0 performance 'Title' 'Current Performance' 'Target Performance' [labels]"
            exit 1
        fi
        create_performance_issue "$2" "$3" "$4" "$5"
        print_status "Performance issue created!"
        ;;
    "domain")
        if [[ $# -lt 3 ]]; then
            print_error "Usage: $0 domain 'Domain Name' 'Target Population' [labels]"
            exit 1
        fi
        create_domain_issue "$2" "$3" "$4"
        print_status "Domain expansion issue created!"
        ;;
    "list")
        if [[ $# -lt 2 ]]; then
            print_error "Usage: $0 list 'label'"
            exit 1
        fi
        list_issues_by_label "$2"
        ;;
    "status" | "dashboard")
        show_project_status
        ;;
    "sync")
        sync_todos_to_issues
        ;;
    "help" | "--help" | "-h")
        echo "ADHDo Issue Management Helper"
        echo "============================="
        echo ""
        echo "Commands:"
        echo "  feature 'title' 'desc' [labels]     - Create feature request"
        echo "  bug 'title' 'desc' 'steps' [labels] - Create bug report"  
        echo "  performance 'title' 'current' 'target' [labels] - Create performance issue"
        echo "  domain 'name' 'population' [labels] - Create domain expansion issue"
        echo "  list 'label'                        - List issues by label"
        echo "  status                              - Show project dashboard"
        echo "  sync                                - Sync todos to issues"
        echo ""
        echo "Examples:"
        echo "  $0 feature 'Add voice input' 'Allow users to speak their requests'"
        echo "  $0 bug 'Chat fails on empty input' 'API returns 500 error' '1. Send empty message 2. See error'"
        echo "  $0 performance 'Optimize LLM response time' '5-6 seconds' '< 2 seconds'"
        echo "  $0 domain 'MCP-Therapy' 'Mental health professionals'"
        echo "  $0 list phase-1"
        echo "  $0 status"
        ;;
    *)
        print_error "Unknown command: $1"
        print_info "Use '$0 help' for usage information"
        exit 1
        ;;
esac