#!/usr/bin/env python3
"""
Execute issue cleanup based on grooming report
"""

import subprocess
import sys

def run_gh_command(command):
    """Run a GitHub CLI command safely"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ Success: {command}")
        print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {command}")
        print(f"   Error: {e.stderr.strip()}")
        return False

def main():
    print("🤖 Executing GitHub Issue Cleanup")
    print("="*50)
    
    # Issues to close (completed features)
    completed_issues = [
        (23, "MCP Client implementation complete"),
        (24, "Gmail Integration complete"), 
        (22, "Google Nest Integration complete"),
        (15, "Telegram Bot Integration complete"),
        (14, "Web Interface complete"),
        (13, "Authentication system complete"),
        (17, "User Onboarding complete")
    ]
    
    # Close completed issues
    print("\n📋 Closing completed issues...")
    for issue_num, reason in completed_issues:
        comment = f"🤖 Auto-closing: {reason}. Implementation verified in codebase."
        
        # Add comment and close
        comment_cmd = f'gh issue comment {issue_num} --body "{comment}"'
        close_cmd = f'gh issue close {issue_num}'
        
        if run_gh_command(comment_cmd):
            run_gh_command(close_cmd)
    
    # Create tracking issues for completed work
    print("\n➕ Creating tracking issues...")
    
    tracking_issues = [
        ("📋 Production Deployment Tracking", "Track production-ready features and deployment status", ["tracking", "milestone"]),
        ("📋 Beta Testing Framework Tracking", "Track beta testing implementation and user feedback", ["tracking", "milestone"]),
        ("📋 Performance Optimization Tracking", "Track performance improvements and benchmarks", ["tracking", "milestone"]),
        ("📋 CI/CD Pipeline Tracking", "Track CI/CD implementation and automation", ["tracking", "milestone"]),
        ("📋 Documentation Portal Tracking", "Track documentation completion and maintenance", ["tracking", "milestone"])
    ]
    
    for title, body, labels in tracking_issues:
        labels_str = ",".join(labels)
        create_cmd = f'gh issue create --title "{title}" --body "{body}" --label "{labels_str}"'
        run_gh_command(create_cmd)
    
    print("\n✅ Issue cleanup completed!")

if __name__ == "__main__":
    main()