#!/usr/bin/env python3
"""
GitHub Issue Grooming Agent for ADHDo Project

This agent automatically reviews GitHub issues and provides recommendations for:
- Issues that should be closed (completed work)
- Issues that need status updates
- Missing issues for completed work
- Better organization/labeling

Usage:
    python scripts/github_issue_grooming.py --analyze-only
    python scripts/github_issue_grooming.py --interactive
    python scripts/github_issue_grooming.py --auto-update
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging

try:
    import requests
except ImportError:
    requests = None

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class GitHubIssueGroomer:
    """Automated GitHub issue grooming for the ADHDo project."""
    
    def __init__(self, github_token: Optional[str] = None, repo_owner: str = None, repo_name: str = None):
        """Initialize the issue groomer."""
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.repo_owner = repo_owner or self._detect_repo_owner()
        self.repo_name = repo_name or self._detect_repo_name()
        
        if not self.github_token:
            logger.warning("No GitHub token provided. Some operations may fail.")
        
        self.headers = {
            'Authorization': f'token {self.github_token}' if self.github_token else '',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        # API endpoints
        self.api_base = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}'
        
        # Codebase analysis data
        self.completed_features = {}
        self.existing_features = {}
        self.recent_commits = []
        
        # Issue tracking
        self.current_issues = {}
        self.issue_recommendations = {
            'close': [],
            'update': [],
            'create': [],
            'relabel': []
        }
    
    def _detect_repo_owner(self) -> str:
        """Detect repository owner from git remote."""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            
            # Parse GitHub URL
            if 'github.com' in remote_url:
                if remote_url.startswith('git@github.com:'):
                    # SSH format: git@github.com:owner/repo.git
                    path = remote_url.split(':')[1]
                elif remote_url.startswith('https://github.com/'):
                    # HTTPS format: https://github.com/owner/repo.git
                    path = remote_url.replace('https://github.com/', '')
                else:
                    raise ValueError(f"Unknown remote format: {remote_url}")
                
                owner = path.split('/')[0]
                return owner
            
            raise ValueError(f"Not a GitHub repository: {remote_url}")
            
        except (subprocess.CalledProcessError, IndexError, ValueError) as e:
            logger.warning(f"Could not detect repo owner: {str(e)}")
            return "owner"
    
    def _detect_repo_name(self) -> str:
        """Detect repository name from git remote."""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            
            # Parse GitHub URL
            if 'github.com' in remote_url:
                if remote_url.startswith('git@github.com:'):
                    # SSH format: git@github.com:owner/repo.git
                    path = remote_url.split(':')[1]
                elif remote_url.startswith('https://github.com/'):
                    # HTTPS format: https://github.com/owner/repo.git
                    path = remote_url.replace('https://github.com/', '')
                else:
                    raise ValueError(f"Unknown remote format: {remote_url}")
                
                repo_name = path.split('/')[1].replace('.git', '')
                return repo_name
            
            raise ValueError(f"Not a GitHub repository: {remote_url}")
            
        except (subprocess.CalledProcessError, IndexError, ValueError) as e:
            logger.warning(f"Could not detect repo name: {str(e)}")
            return "repo"
    
    def analyze_codebase(self):
        """Analyze codebase to identify completed features."""
        logger.info("Analyzing codebase for completed features...")
        
        # Get recent commits
        self._analyze_recent_commits()
        
        # Analyze feature completeness
        self._analyze_feature_completeness()
        
        logger.info(f"Codebase analysis complete - completed_features: {len(self.completed_features)}, recent_commits: {len(self.recent_commits)}")
    
    def _analyze_recent_commits(self):
        """Analyze recent commits for completion indicators."""
        try:
            # Get commits from last 30 days
            since_date = (datetime.now() - timedelta(days=30)).isoformat()
            
            result = subprocess.run([
                'git', 'log', 
                '--since', since_date,
                '--pretty=format:%H|%s|%ad|%an',
                '--date=iso',
                '--no-merges'
            ], capture_output=True, text=True, check=True)
            
            commit_lines = result.stdout.strip().split('\n')
            
            for line in commit_lines:
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    commit_hash, message, date, author = parts[:4]
                    
                    self.recent_commits.append({
                        'hash': commit_hash,
                        'message': message,
                        'date': date,
                        'author': author,
                        'completion_indicators': self._extract_completion_indicators(message)
                    })
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to analyze commits: {str(e)}")
    
    def _extract_completion_indicators(self, commit_message: str) -> List[str]:
        """Extract completion indicators from commit message."""
        indicators = []
        message_lower = commit_message.lower()
        
        # Completion keywords
        completion_patterns = [
            r'complete[ds]?',
            r'implement[eds]?',
            r'finish[eds]?',
            r'ready',
            r'production.ready',
            r'beta.ready',
            r'mvp',
            r'done',
            r'✅',
            r'🎉',
            r'🚀'
        ]
        
        for pattern in completion_patterns:
            if re.search(pattern, message_lower):
                indicators.append(pattern)
        
        # Extract feature names
        feature_patterns = [
            r'mcp.?client',
            r'gmail.?integration',
            r'nest.?integration',
            r'google.?home',
            r'calendar.?integration',
            r'telegram.?bot',
            r'web.?interface',
            r'authentication',
            r'registration',
            r'onboarding',
            r'testing.?suite',
            r'performance'
        ]
        
        for pattern in feature_patterns:
            if re.search(pattern, message_lower):
                indicators.append(f"feature:{pattern}")
        
        return indicators
    
    def _analyze_feature_completeness(self):
        """Analyze which features are actually implemented."""
        logger.info("Analyzing feature completeness...")
        
        # Check for MCP Client implementation
        mcp_client_files = [
            'src/mcp_client/__init__.py',
            'src/mcp_client/client.py',
            'src/mcp_client/auth.py',
            'src/mcp_client/browser_auth.py',
            'src/mcp_client/workflow.py'
        ]
        
        if all(Path(f).exists() for f in mcp_client_files):
            self.completed_features['mcp_client'] = {
                'status': 'complete',
                'evidence': mcp_client_files,
                'commit_refs': [c for c in self.recent_commits if 'mcp' in c['message'].lower()]
            }
        
        # Check for Gmail integration
        gmail_files = [
            'src/mcp_tools/gmail_tool.py'
        ]
        
        if all(Path(f).exists() for f in gmail_files):
            # Verify implementation completeness
            gmail_tool_path = Path('src/mcp_tools/gmail_tool.py')
            if gmail_tool_path.exists():
                content = gmail_tool_path.read_text()
                if 'class GmailTool' in content and 'async def invoke' in content:
                    self.completed_features['gmail_integration'] = {
                        'status': 'complete',
                        'evidence': gmail_files,
                        'commit_refs': [c for c in self.recent_commits if 'gmail' in c['message'].lower()]
                    }
        
        # Check for Google Nest integration
        nest_files = [
            'src/mcp_tools/nest_tool.py'
        ]
        
        if all(Path(f).exists() for f in nest_files):
            nest_tool_path = Path('src/mcp_tools/nest_tool.py')
            if nest_tool_path.exists():
                content = nest_tool_path.read_text()
                if 'class NestTool' in content and 'async def invoke' in content:
                    self.completed_features['nest_integration'] = {
                        'status': 'complete',
                        'evidence': nest_files,
                        'commit_refs': [c for c in self.recent_commits if any(word in c['message'].lower() for word in ['nest', 'google home'])]
                    }
        
        # Check for Telegram bot
        telegram_files = [
            'src/mcp_server/telegram_bot.py'
        ]
        
        if all(Path(f).exists() for f in telegram_files):
            self.completed_features['telegram_bot'] = {
                'status': 'complete',
                'evidence': telegram_files,
                'commit_refs': [c for c in self.recent_commits if 'telegram' in c['message'].lower()]
            }
        
        # Check for web interface
        web_files = [
            'static/index.html',
            'static/dashboard.html',
            'static/mcp_setup.html'
        ]
        
        if all(Path(f).exists() for f in web_files):
            self.completed_features['web_interface'] = {
                'status': 'complete',
                'evidence': web_files,
                'commit_refs': [c for c in self.recent_commits if 'web' in c['message'].lower() or 'interface' in c['message'].lower()]
            }
        
        # Check for authentication system
        auth_files = [
            'src/mcp_server/auth.py',
            'src/mcp_client/auth.py',
            'src/mcp_client/browser_auth.py'
        ]
        
        if all(Path(f).exists() for f in auth_files):
            self.completed_features['authentication'] = {
                'status': 'complete',
                'evidence': auth_files,
                'commit_refs': [c for c in self.recent_commits if 'auth' in c['message'].lower()]
            }
        
        # Check for onboarding system
        onboarding_files = [
            'src/mcp_server/onboarding.py',
            'src/mcp_server/beta_onboarding.py'
        ]
        
        if all(Path(f).exists() for f in onboarding_files):
            self.completed_features['onboarding'] = {
                'status': 'complete',
                'evidence': onboarding_files,
                'commit_refs': [c for c in self.recent_commits if 'onboard' in c['message'].lower()]
            }
        
        # Check for testing suite
        test_dirs = [
            'tests/unit',
            'tests/integration',
            'tests/e2e',
            'tests/performance'
        ]
        
        if all(Path(d).exists() for d in test_dirs):
            self.completed_features['testing_suite'] = {
                'status': 'complete',
                'evidence': test_dirs,
                'commit_refs': [c for c in self.recent_commits if 'test' in c['message'].lower()]
            }
    
    def fetch_github_issues(self) -> List[Dict]:
        """Fetch current GitHub issues."""
        if not self.github_token or not requests:
            logger.warning("No GitHub token or requests library - using mock issues")
            return self._get_mock_issues()
        
        try:
            # Fetch all open issues
            url = f"{self.api_base}/issues"
            params = {
                'state': 'open',
                'per_page': 100,
                'sort': 'created',
                'direction': 'desc'
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            issues = response.json()
            
            # Store issues by number for easy lookup
            for issue in issues:
                self.current_issues[issue['number']] = issue
            
            logger.info(f"Fetched GitHub issues: {len(issues)}")
            return issues
            
        except Exception as e:
            logger.error(f"Failed to fetch GitHub issues: {str(e)}")
            return self._get_mock_issues()
    
    def _get_mock_issues(self) -> List[Dict]:
        """Get mock issues for testing when GitHub API is not available."""
        mock_issues = [
            {
                'number': 25,
                'title': '📅 Google Calendar Integration for ADHD Time Management',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'integration'}],
                'created_at': '2024-01-15T10:00:00Z',
                'updated_at': '2024-01-16T10:00:00Z'
            },
            {
                'number': 24,
                'title': '📧 Gmail Integration for Email-Based ADHD Support',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'integration'}],
                'created_at': '2024-01-14T10:00:00Z',
                'updated_at': '2024-01-15T10:00:00Z'
            },
            {
                'number': 23,
                'title': '🔌 Implement Model Context Protocol (MCP) Client for Universal Tool Integration',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'core'}],
                'created_at': '2024-01-13T10:00:00Z',
                'updated_at': '2024-01-14T10:00:00Z'
            },
            {
                'number': 22,
                'title': '🏠 Google Home + Wearable Integration for Watch Nudges & Biometric Data',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'integration'}],
                'created_at': '2024-01-12T10:00:00Z',
                'updated_at': '2024-01-13T10:00:00Z'
            },
            {
                'number': 15,
                'title': '🤖 Telegram Bot Integration and Nudge System',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'bot'}],
                'created_at': '2024-01-05T10:00:00Z',
                'updated_at': '2024-01-06T10:00:00Z'
            },
            {
                'number': 14,
                'title': '🎨 Build ADHD-Optimized Web Interface',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'ui'}],
                'created_at': '2024-01-04T10:00:00Z',
                'updated_at': '2024-01-05T10:00:00Z'
            },
            {
                'number': 13,
                'title': '🔐 Complete User Registration and Login API',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'auth'}],
                'created_at': '2024-01-03T10:00:00Z',
                'updated_at': '2024-01-04T10:00:00Z'
            },
            {
                'number': 17,
                'title': '🚀 User Onboarding and Welcome Experience',
                'state': 'open',
                'labels': [{'name': 'enhancement'}, {'name': 'ux'}],
                'created_at': '2024-01-07T10:00:00Z',
                'updated_at': '2024-01-08T10:00:00Z'
            }
        ]
        
        for issue in mock_issues:
            self.current_issues[issue['number']] = issue
        
        return mock_issues
    
    def analyze_issue_status(self):
        """Analyze current issues against completed features."""
        logger.info("Analyzing issue status...")
        
        # Map completed features to issue numbers
        feature_to_issue_mapping = {
            'mcp_client': [23],
            'gmail_integration': [24],
            'nest_integration': [22],
            'telegram_bot': [15],
            'web_interface': [14],
            'authentication': [13],
            'onboarding': [17]
        }
        
        # Check which issues should be closed
        for feature, issue_numbers in feature_to_issue_mapping.items():
            if feature in self.completed_features:
                for issue_num in issue_numbers:
                    if issue_num in self.current_issues:
                        issue = self.current_issues[issue_num]
                        self.issue_recommendations['close'].append({
                            'issue_number': issue_num,
                            'title': issue['title'],
                            'reason': f'Feature "{feature}" has been completed',
                            'evidence': self.completed_features[feature]['evidence'],
                            'commit_refs': [c['message'] for c in self.completed_features[feature]['commit_refs']]
                        })
        
        # Identify issues that need updates
        self._identify_update_candidates()
        
        # Identify missing issues for completed work
        self._identify_missing_issues()
        
        # Identify issues that need better labeling
        self._identify_relabeling_candidates()
    
    def _identify_update_candidates(self):
        """Identify issues that need status updates."""
        for issue_num, issue in self.current_issues.items():
            title = issue['title'].lower()
            
            # Check if issue has been stale for a while
            updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
            days_since_update = (datetime.now(updated_at.tzinfo) - updated_at).days
            
            if days_since_update > 14:  # More than 2 weeks
                self.issue_recommendations['update'].append({
                    'issue_number': issue_num,
                    'title': issue['title'],
                    'reason': f'No updates for {days_since_update} days',
                    'suggestion': 'Update with current progress or close if completed'
                })
            
            # Check if issue might be partially complete
            if 'calendar' in title and days_since_update > 7:
                self.issue_recommendations['update'].append({
                    'issue_number': issue_num,
                    'title': issue['title'],
                    'reason': 'Calendar integration may be in progress',
                    'suggestion': 'Update with current implementation status'
                })
    
    def _identify_missing_issues(self):
        """Identify issues that should exist for completed work."""
        completed_work_missing_issues = []
        
        # Check if major milestones have issues
        major_milestones = [
            'Production Deployment',
            'Beta Testing Framework',
            'Performance Optimization',
            'CI/CD Pipeline',
            'Documentation Portal'
        ]
        
        for milestone in major_milestones:
            # Check if there's evidence of this work in commits
            relevant_commits = [
                c for c in self.recent_commits
                if any(keyword in c['message'].lower() 
                      for keyword in milestone.lower().split())
            ]
            
            if relevant_commits:
                self.issue_recommendations['create'].append({
                    'title': f'📋 {milestone} Tracking',
                    'reason': f'Found {len(relevant_commits)} commits related to {milestone}',
                    'labels': ['tracking', 'milestone'],
                    'commit_evidence': [c['message'] for c in relevant_commits[:3]]
                })
    
    def _identify_relabeling_candidates(self):
        """Identify issues that need better labels."""
        for issue_num, issue in self.current_issues.items():
            current_labels = [label['name'] for label in issue.get('labels', [])]
            title = issue['title'].lower()
            
            suggested_labels = []
            
            # Suggest labels based on title content
            if 'integration' in title and 'integration' not in current_labels:
                suggested_labels.append('integration')
            
            if any(word in title for word in ['bug', 'fix', 'error']) and 'bug' not in current_labels:
                suggested_labels.append('bug')
            
            if any(word in title for word in ['feature', 'enhancement', 'add']) and 'enhancement' not in current_labels:
                suggested_labels.append('enhancement')
            
            if any(word in title for word in ['urgent', 'critical', 'blocker']) and 'high-priority' not in current_labels:
                suggested_labels.append('high-priority')
            
            if any(word in title for word in ['adhd', 'accessibility', 'ux']) and 'adhd-specific' not in current_labels:
                suggested_labels.append('adhd-specific')
            
            if suggested_labels:
                self.issue_recommendations['relabel'].append({
                    'issue_number': issue_num,
                    'title': issue['title'],
                    'current_labels': current_labels,
                    'suggested_labels': suggested_labels,
                    'reason': 'Improve issue categorization'
                })
    
    def generate_recommendations_report(self) -> str:
        """Generate a comprehensive recommendations report."""
        report = []
        report.append("# 🤖 GitHub Issue Grooming Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("## 📊 Summary")
        report.append(f"- **Issues to Close:** {len(self.issue_recommendations['close'])}")
        report.append(f"- **Issues to Update:** {len(self.issue_recommendations['update'])}")
        report.append(f"- **Issues to Create:** {len(self.issue_recommendations['create'])}")
        report.append(f"- **Issues to Relabel:** {len(self.issue_recommendations['relabel'])}")
        report.append(f"- **Completed Features:** {len(self.completed_features)}")
        report.append("")
        
        # Completed Features
        report.append("## ✅ Completed Features Analysis")
        for feature, info in self.completed_features.items():
            report.append(f"### {feature.replace('_', ' ').title()}")
            report.append(f"- **Status:** {info['status']}")
            report.append(f"- **Evidence:** {', '.join(info['evidence'])}")
            if info['commit_refs']:
                report.append("- **Recent Commits:**")
                for commit in info['commit_refs'][:3]:
                    report.append(f"  - {commit['message'][:80]}...")
            report.append("")
        
        # Issues to Close
        if self.issue_recommendations['close']:
            report.append("## 🔒 Issues Ready to Close")
            for rec in self.issue_recommendations['close']:
                report.append(f"### Issue #{rec['issue_number']}: {rec['title']}")
                report.append(f"**Reason:** {rec['reason']}")
                report.append(f"**Evidence:** {', '.join(rec['evidence'])}")
                if rec['commit_refs']:
                    report.append("**Supporting Commits:**")
                    for commit_msg in rec['commit_refs'][:2]:
                        report.append(f"- {commit_msg}")
                report.append("")
        
        # Issues to Update
        if self.issue_recommendations['update']:
            report.append("## 🔄 Issues Needing Updates")
            for rec in self.issue_recommendations['update']:
                report.append(f"### Issue #{rec['issue_number']}: {rec['title']}")
                report.append(f"**Reason:** {rec['reason']}")
                report.append(f"**Suggestion:** {rec['suggestion']}")
                report.append("")
        
        # Issues to Create
        if self.issue_recommendations['create']:
            report.append("## ➕ Suggested New Issues")
            for rec in self.issue_recommendations['create']:
                report.append(f"### {rec['title']}")
                report.append(f"**Reason:** {rec['reason']}")
                report.append(f"**Suggested Labels:** {', '.join(rec['labels'])}")
                if rec.get('commit_evidence'):
                    report.append("**Supporting Evidence:**")
                    for evidence in rec['commit_evidence']:
                        report.append(f"- {evidence}")
                report.append("")
        
        # Issues to Relabel
        if self.issue_recommendations['relabel']:
            report.append("## 🏷️ Labeling Improvements")
            for rec in self.issue_recommendations['relabel']:
                report.append(f"### Issue #{rec['issue_number']}: {rec['title']}")
                report.append(f"**Current Labels:** {', '.join(rec['current_labels']) if rec['current_labels'] else 'None'}")
                report.append(f"**Suggested Labels:** {', '.join(rec['suggested_labels'])}")
                report.append(f"**Reason:** {rec['reason']}")
                report.append("")
        
        # Action Items
        report.append("## 🎯 Immediate Action Items")
        report.append("")
        report.append("### High Priority")
        high_priority_actions = []
        
        if self.issue_recommendations['close']:
            high_priority_actions.append(f"✅ **Close {len(self.issue_recommendations['close'])} completed issues** - These represent finished work and should be closed immediately")
        
        stale_updates = [r for r in self.issue_recommendations['update'] if 'days' in r['reason'] and int(r['reason'].split()[3]) > 21]
        if stale_updates:
            high_priority_actions.append(f"🔄 **Update {len(stale_updates)} stale issues** - These haven't been updated in over 3 weeks")
        
        for action in high_priority_actions:
            report.append(f"1. {action}")
        
        report.append("")
        report.append("### Medium Priority")
        medium_priority_actions = []
        
        if self.issue_recommendations['create']:
            medium_priority_actions.append(f"➕ **Create {len(self.issue_recommendations['create'])} tracking issues** - Document completed work that lacks issue tracking")
        
        if self.issue_recommendations['relabel']:
            medium_priority_actions.append(f"🏷️ **Improve labels on {len(self.issue_recommendations['relabel'])} issues** - Better categorization for project management")
        
        for action in medium_priority_actions:
            report.append(f"1. {action}")
        
        # Automation Suggestions
        report.append("")
        report.append("## 🤖 Automation Recommendations")
        report.append("")
        report.append("Consider implementing these automated workflows:")
        report.append("")
        report.append("1. **Auto-close issues on feature completion** - When commits contain 'closes #123' or 'fixes #123'")
        report.append("2. **Stale issue detection** - Weekly check for issues without updates > 2 weeks")
        report.append("3. **Auto-labeling** - Label issues based on title keywords and file paths in commits")
        report.append("4. **Milestone tracking** - Auto-create milestone issues when major features are completed")
        report.append("5. **Progress updates** - Weekly summary of issue status changes")
        
        return "\n".join(report)
    
    def execute_recommendations(self, action_type: str = 'all', dry_run: bool = True):
        """Execute the grooming recommendations."""
        if not self.github_token and not dry_run:
            logger.error("Cannot execute recommendations without GitHub token")
            return False
        
        logger.info(f"Executing recommendations - action_type: {action_type}, dry_run: {dry_run}")
        
        if action_type in ['all', 'close']:
            self._execute_close_recommendations(dry_run)
        
        if action_type in ['all', 'update']:
            self._execute_update_recommendations(dry_run)
        
        if action_type in ['all', 'create']:
            self._execute_create_recommendations(dry_run)
        
        if action_type in ['all', 'relabel']:
            self._execute_relabel_recommendations(dry_run)
        
        return True
    
    def _execute_close_recommendations(self, dry_run: bool):
        """Execute issue close recommendations."""
        for rec in self.issue_recommendations['close']:
            issue_num = rec['issue_number']
            
            if dry_run:
                logger.info(f"DRY RUN: Would close issue {issue_num}")
                continue
            
            try:
                # Add closing comment
                comment_body = f"""🤖 **Auto-closing completed issue**

{rec['reason']}

**Evidence of completion:**
{chr(10).join(f'- {evidence}' for evidence in rec['evidence'])}

**Supporting commits:**
{chr(10).join(f'- {commit}' for commit in rec['commit_refs'][:3])}

This issue has been automatically closed by the GitHub Issue Grooming Agent.
If this was closed in error, please reopen and add the `keep-open` label.
"""
                
                # Post comment
                comment_url = f"{self.api_base}/issues/{issue_num}/comments"
                comment_response = requests.post(
                    comment_url,
                    headers=self.headers,
                    json={'body': comment_body}
                )
                comment_response.raise_for_status()
                
                # Close issue
                close_url = f"{self.api_base}/issues/{issue_num}"
                close_response = requests.patch(
                    close_url,
                    headers=self.headers,
                    json={'state': 'closed'}
                )
                close_response.raise_for_status()
                
                logger.info(f"Closed issue {issue_num}")
                
            except Exception as e:
                logger.error(f"Failed to close issue {issue_num}: {str(e)}")
    
    def _execute_update_recommendations(self, dry_run: bool):
        """Execute issue update recommendations."""
        for rec in self.issue_recommendations['update']:
            issue_num = rec['issue_number']
            
            if dry_run:
                logger.info(f"DRY RUN: Would update issue {issue_num}")
                continue
            
            try:
                comment_body = f"""🤖 **Status Update Request**

{rec['reason']}

**Suggested Action:** {rec['suggestion']}

Please provide an update on the current status of this issue. If this work has been completed, please close the issue. If it's still in progress, please update the description with the current status.

*This comment was posted by the GitHub Issue Grooming Agent.*
"""
                
                comment_url = f"{self.api_base}/issues/{issue_num}/comments"
                response = requests.post(
                    comment_url,
                    headers=self.headers,
                    json={'body': comment_body}
                )
                response.raise_for_status()
                
                logger.info(f"Updated issue {issue_num}")
                
            except Exception as e:
                logger.error(f"Failed to update issue {issue_num}: {str(e)}")
    
    def _execute_create_recommendations(self, dry_run: bool):
        """Execute issue creation recommendations."""
        for rec in self.issue_recommendations['create']:
            if dry_run:
                logger.info(f"DRY RUN: Would create issue: {rec['title']}")
                continue
            
            try:
                issue_body = f"""{rec['reason']}

## Evidence

{chr(10).join(f'- {evidence}' for evidence in rec.get('commit_evidence', []))}

## Next Steps

- [ ] Document current implementation status
- [ ] Identify any remaining work
- [ ] Update project milestones

*This issue was created by the GitHub Issue Grooming Agent to track completed work.*
"""
                
                create_url = f"{self.api_base}/issues"
                response = requests.post(
                    create_url,
                    headers=self.headers,
                    json={
                        'title': rec['title'],
                        'body': issue_body,
                        'labels': rec['labels']
                    }
                )
                response.raise_for_status()
                
                new_issue = response.json()
                logger.info(f"Created issue {new_issue['number']}: {rec['title']}")
                
            except Exception as e:
                logger.error(f"Failed to create issue '{rec['title']}': {str(e)}")
    
    def _execute_relabel_recommendations(self, dry_run: bool):
        """Execute issue relabeling recommendations."""
        for rec in self.issue_recommendations['relabel']:
            issue_num = rec['issue_number']
            
            if dry_run:
                logger.info(f"DRY RUN: Would relabel issue {issue_num}")
                continue
            
            try:
                # Get current labels and add suggested ones
                current_labels = rec['current_labels']
                all_labels = list(set(current_labels + rec['suggested_labels']))
                
                relabel_url = f"{self.api_base}/issues/{issue_num}"
                response = requests.patch(
                    relabel_url,
                    headers=self.headers,
                    json={'labels': all_labels}
                )
                response.raise_for_status()
                
                logger.info(f"Relabeled issue {issue_num}, added labels: {rec['suggested_labels']}")
                
            except Exception as e:
                logger.error(f"Failed to relabel issue {issue_num}: {str(e)}")
    
    def run_full_analysis(self, output_file: Optional[str] = None) -> str:
        """Run complete issue grooming analysis."""
        logger.info("Starting full issue grooming analysis...")
        
        # Step 1: Analyze codebase
        self.analyze_codebase()
        
        # Step 2: Fetch GitHub issues
        self.fetch_github_issues()
        
        # Step 3: Analyze issue status
        self.analyze_issue_status()
        
        # Step 4: Generate report
        report = self.generate_recommendations_report()
        
        # Step 5: Save report if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved: {output_file}")
        
        logger.info("Issue grooming analysis complete")
        return report


def main():
    """Main entry point for the issue grooming agent."""
    parser = argparse.ArgumentParser(
        description="GitHub Issue Grooming Agent for ADHDo Project"
    )
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze and generate report, do not make changes'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode for reviewing recommendations'
    )
    parser.add_argument(
        '--auto-update',
        action='store_true',
        help='Automatically execute safe recommendations'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='issue_grooming_report.md',
        help='Output file for the grooming report'
    )
    parser.add_argument(
        '--github-token',
        type=str,
        help='GitHub personal access token'
    )
    
    args = parser.parse_args()
    
    # Initialize groomer
    groomer = GitHubIssueGroomer(github_token=args.github_token)
    
    # Run analysis
    report = groomer.run_full_analysis(args.output)
    
    if args.analyze_only:
        print("📊 Analysis complete! Report generated.")
        print(f"📄 Report saved to: {args.output}")
        
    elif args.interactive:
        print("🤖 Interactive Issue Grooming")
        print("=" * 50)
        print(report)
        print("=" * 50)
        
        while True:
            print("\nAvailable actions:")
            print("1. Close completed issues")
            print("2. Update stale issues") 
            print("3. Create tracking issues")
            print("4. Improve issue labels")
            print("5. Execute all recommendations")
            print("6. Dry run all recommendations")
            print("7. Exit")
            
            choice = input("\nSelect action (1-7): ").strip()
            
            if choice == '1':
                groomer.execute_recommendations('close', dry_run=False)
            elif choice == '2':
                groomer.execute_recommendations('update', dry_run=False)
            elif choice == '3':
                groomer.execute_recommendations('create', dry_run=False)
            elif choice == '4':
                groomer.execute_recommendations('relabel', dry_run=False)
            elif choice == '5':
                groomer.execute_recommendations('all', dry_run=False)
            elif choice == '6':
                groomer.execute_recommendations('all', dry_run=True)
            elif choice == '7':
                break
            else:
                print("Invalid choice. Please try again.")
    
    elif args.auto_update:
        print("🤖 Auto-updating issues...")
        
        # Only execute safe actions automatically
        # Close completed issues and update stale ones
        groomer.execute_recommendations('close', dry_run=False)
        groomer.execute_recommendations('update', dry_run=False)
        
        print("✅ Auto-update complete!")
    
    else:
        print("📊 Analysis complete!")
        print(f"📄 Report: {args.output}")
        print("\nUse --interactive to review and execute recommendations")


if __name__ == "__main__":
    main()