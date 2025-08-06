# 🤖 GitHub Issue Grooming System

A comprehensive automated system for maintaining GitHub issue hygiene in the ADHDo project. This system analyzes the codebase, tracks completed features, and provides intelligent recommendations for issue management.

## 🎯 Overview

The Issue Grooming System consists of:

1. **Automated Analysis Agent** (`scripts/github_issue_grooming.py`)
2. **Easy-to-use Runner Script** (`scripts/run_issue_grooming.sh`)  
3. **GitHub Actions Workflow** (`.github/workflows/issue-grooming.yml`)
4. **Comprehensive Reporting** (Markdown reports with actionable recommendations)

## 🚀 Quick Start

### Basic Usage

```bash
# Analyze issues and generate report
./scripts/run_issue_grooming.sh analyze

# Interactive mode for manual review
./scripts/run_issue_grooming.sh interactive --token $GITHUB_TOKEN

# Automatically execute safe recommendations
./scripts/run_issue_grooming.sh auto --token $GITHUB_TOKEN

# Dry run to see what would be done
./scripts/run_issue_grooming.sh dry-run
```

### GitHub Actions

The system runs automatically:
- **Weekly**: Every Sunday at 12:00 UTC
- **Manual**: Via workflow dispatch with mode selection
- **Pull Requests**: Automatically creates PRs with recommendations

## 📊 Features

### Completed Feature Detection

The system automatically detects completed features by analyzing:

- ✅ **File existence** - Checks for implementation files
- ✅ **Code completeness** - Verifies core functionality is implemented  
- ✅ **Recent commits** - Analyzes commit messages for completion indicators
- ✅ **Evidence gathering** - Collects supporting evidence for decisions

**Currently Detected Features:**
- MCP Client Framework
- Gmail Integration  
- Google Nest Integration
- Telegram Bot
- Web Interface
- Authentication System
- User Onboarding
- Testing Suite

### Issue Analysis Categories

#### 🔒 Issues Ready to Close
- Features confirmed complete with file evidence
- Supporting commit references
- Automatic closure recommendations

#### 🔄 Issues Needing Updates
- Stale issues (>2 weeks without updates)
- Issues with potential progress
- Status clarification requests

#### ➕ Suggested New Issues  
- Missing tracking for completed work
- Major milestone tracking
- Documentation gaps

#### 🏷️ Labeling Improvements
- ADHD-specific feature labeling
- Integration vs core feature classification
- Priority level assignments

## 🛠️ System Components

### Core Grooming Agent

**File:** `scripts/github_issue_grooming.py`

**Key Classes:**
- `GitHubIssueGroomer` - Main orchestration class
- Feature detection algorithms
- GitHub API integration
- Report generation engine

**Analysis Methods:**
- `analyze_codebase()` - Scans for completed features
- `fetch_github_issues()` - Retrieves current issue state
- `analyze_issue_status()` - Matches features to issues
- `generate_recommendations_report()` - Creates actionable reports

### Runner Script

**File:** `scripts/run_issue_grooming.sh`

**Modes:**
- `analyze` - Generate analysis report only
- `interactive` - Manual review and execution
- `auto` - Execute safe recommendations automatically
- `dry-run` - Show actions without execution

**Features:**
- Dependency checking
- Environment setup
- Colorized output
- Progress reporting

### GitHub Actions Workflow

**File:** `.github/workflows/issue-grooming.yml`

**Capabilities:**
- Scheduled execution (weekly)
- Manual triggering with mode selection
- Automatic PR creation with recommendations
- Artifact storage for reports
- Team notifications

## 📋 Current Analysis Results

Based on the latest analysis of the ADHDo codebase:

### ✅ Completed Features (8 total)
1. **MCP Client Framework** - Complete implementation with OAuth
2. **Gmail Integration** - Full ADHD-optimized email tool
3. **Google Nest Integration** - Smart home nudge system  
4. **Telegram Bot** - Notification and interaction system
5. **Web Interface** - ADHD-friendly dashboard and setup
6. **Authentication System** - Complete OAuth and session management
7. **User Onboarding** - Automated beta user setup
8. **Testing Suite** - Comprehensive unit/integration/e2e tests

### 🔒 Issues to Close Immediately (7 total)
- #23: MCP Client Implementation ✅ COMPLETE
- #24: Gmail Integration ✅ COMPLETE  
- #22: Google Nest Integration ✅ COMPLETE
- #15: Telegram Bot ✅ COMPLETE
- #14: Web Interface ✅ COMPLETE
- #13: Authentication API ✅ COMPLETE
- #17: User Onboarding ✅ COMPLETE

### 🔄 Issues Needing Updates
- #25: Calendar Integration - Status unclear, needs progress update

### ➕ Recommended New Issues (5 total)
1. Production Deployment Tracking
2. Beta Testing Framework Tracking  
3. Performance Optimization Tracking
4. CI/CD Pipeline Tracking
5. Documentation Portal Tracking

## 🎯 Immediate Action Plan

### High Priority (Do Now)
1. **Close 7 completed issues** - Clear wins, should be closed immediately
2. **Update Calendar Integration issue** - Clarify current status

### Medium Priority (This Week)  
1. **Create 5 tracking issues** - Document major completed work
2. **Improve labeling** - Add ADHD-specific and integration labels
3. **Set up automation** - Configure weekly grooming runs

### Long-term (This Month)
1. **Implement auto-close on completion** - Link commits to issues
2. **Create project boards** - Organize issues by feature area
3. **Set up milestone tracking** - Plan future releases

## 🔧 Configuration

### Environment Variables

```bash
# Required for GitHub API access
export GITHUB_TOKEN="your_github_token_here"

# Optional: Custom repository (auto-detected by default)
export GITHUB_REPO_OWNER="your_org"
export GITHUB_REPO_NAME="your_repo"
```

### GitHub Token Permissions

Required scopes:
- `repo` - Full repository access
- `issues` - Read and write issues
- `pull_requests` - Create pull requests (for automated reports)

### Customization

The system can be customized by modifying:

**Feature Detection Rules** (`_analyze_feature_completeness`):
```python
# Add new feature detection
self.completed_features['new_feature'] = {
    'status': 'complete',
    'evidence': ['path/to/file.py'],
    'commit_refs': matching_commits
}
```

**Issue Mapping** (`analyze_issue_status`):  
```python
# Map features to issue numbers
feature_to_issue_mapping = {
    'new_feature': [issue_number]
}
```

**Completion Indicators** (`_extract_completion_indicators`):
```python
# Add custom completion patterns
completion_patterns = [
    r'your_custom_pattern',
    r'✨',  # Custom emoji
]
```

## 📚 Usage Examples

### Development Workflow

```bash
# Daily: Quick status check
./scripts/run_issue_grooming.sh analyze

# Weekly: Full interactive review
./scripts/run_issue_grooming.sh interactive --token $GITHUB_TOKEN

# Before releases: Auto-cleanup
./scripts/run_issue_grooming.sh auto --token $GITHUB_TOKEN
```

### CI/CD Integration

```yaml
# In your workflow
- name: Groom issues
  run: |
    ./scripts/run_issue_grooming.sh auto --token ${{ secrets.GITHUB_TOKEN }}
```

### Custom Reports

```bash
# Custom output location
python scripts/github_issue_grooming.py \
  --analyze-only \
  --output custom_report.md \
  --github-token $GITHUB_TOKEN
```

## 🤖 Automation Recommendations

### Immediate Automation Opportunities

1. **Auto-close on completion**
   ```bash
   # Commit message format
   git commit -m "✅ Complete feature XYZ (closes #123)"
   ```

2. **Stale issue detection**
   - Weekly checks for issues >2 weeks old
   - Automatic status request comments

3. **Auto-labeling**
   - Label based on title keywords
   - ADHD-specific feature detection
   - Integration vs core classification

### Future Enhancements

1. **Intelligent Priority Assignment**
   - Analyze commit frequency
   - User engagement metrics
   - Business impact scoring

2. **Progress Tracking**
   - Automated progress updates
   - Milestone achievement detection
   - Release readiness assessment

3. **Team Collaboration**
   - Assignee recommendations
   - Workload balancing
   - Expertise mapping

## 🐛 Troubleshooting

### Common Issues

**Permission denied executing script:**
```bash
chmod +x scripts/run_issue_grooming.sh
```

**Missing Python dependencies:**
```bash
pip install requests structlog
```

**GitHub API rate limiting:**
- Use GitHub token for higher limits
- Add delays between API calls
- Use mock data for development

**No issues detected for closure:**
- Check feature detection logic
- Verify file paths exist
- Review commit message patterns

### Debug Mode

```bash
# Enable verbose logging
./scripts/run_issue_grooming.sh analyze --verbose

# Python debug mode
python -d scripts/github_issue_grooming.py --analyze-only
```

### Logging

The system logs to:
- **Console** - Real-time progress
- **Reports** - Detailed analysis results
- **GitHub Actions** - Workflow summaries
- **Artifacts** - Persistent report storage

## 📈 Metrics and Analytics

### Issue Health Metrics

- **Closure Rate** - Issues closed vs opened
- **Staleness** - Average days without updates  
- **Completion Detection** - Automated vs manual closures
- **Label Coverage** - Percentage of issues with proper labels

### Feature Delivery Metrics

- **Feature Completion** - Delivered vs planned
- **Implementation Quality** - Evidence strength scores
- **Documentation Coverage** - Issues with tracking
- **Release Readiness** - Features ready for production

### Process Improvement Metrics

- **Automation Rate** - Automated vs manual actions
- **Accuracy** - False positive/negative rates
- **Time Savings** - Manual effort reduced
- **Team Satisfaction** - Developer experience metrics

## 🔮 Future Roadmap

### Short-term (Next Month)
- [ ] Integration with project boards
- [ ] Slack/Discord notifications  
- [ ] Custom completion patterns
- [ ] Performance optimization

### Medium-term (Next Quarter)
- [ ] Machine learning for issue classification
- [ ] Integration with development tools (IDEs, etc.)
- [ ] Advanced analytics dashboard
- [ ] Multi-repository support

### Long-term (Next Year)
- [ ] Intelligent priority recommendations
- [ ] Automated milestone planning
- [ ] Team workload optimization  
- [ ] Predictive issue management

## 🤝 Contributing

### Adding New Features

1. **Feature Detection** - Add to `_analyze_feature_completeness()`
2. **Issue Mapping** - Update `analyze_issue_status()`
3. **Testing** - Add test cases and documentation
4. **Commit Patterns** - Update completion indicators

### Improving Accuracy

1. **False Positives** - Add exclusion rules
2. **False Negatives** - Expand detection patterns
3. **Edge Cases** - Handle special scenarios
4. **Validation** - Add verification steps

### Custom Workflows

The system is designed to be extensible. Create custom workflows by:

1. Subclassing `GitHubIssueGroomer`
2. Overriding analysis methods
3. Adding custom recommendation types
4. Implementing domain-specific logic

## 📝 License and Credits

This issue grooming system was developed specifically for the ADHDo project as part of the MCP (Meta-Cognitive Protocol) architecture. It implements neurodiversity-affirming principles in both its functionality and development approach.

**Key Principles:**
- **Reduce cognitive load** - Automate repetitive tasks
- **Clear communication** - Structured, actionable reports
- **Executive function support** - Automated organization and tracking
- **Transparency** - Open source and well-documented

---

*For questions, issues, or contributions, please refer to the main project documentation or open an issue with the `issue-grooming` label.*