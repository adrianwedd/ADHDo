"""
GitHub Issue Automation System for ADHDo Project

Enterprise-level GitHub issue lifecycle management with intelligent automation,
scalable processing, and comprehensive audit trails.

Building the future, one line of code at a time.
"""

__version__ = "1.0.0"
__author__ = "CODEFORGE Systems Architecture Team"

from .automation_engine import GitHubAutomationEngine
from .issue_tracker import IssueTracker
from .feature_detector import FeatureDetector
from .webhook_handler import WebhookHandler
from .audit_logger import AuditLogger
from .rollback_manager import RollbackManager

__all__ = [
    "GitHubAutomationEngine",
    "IssueTracker", 
    "FeatureDetector",
    "WebhookHandler",
    "AuditLogger",
    "RollbackManager"
]