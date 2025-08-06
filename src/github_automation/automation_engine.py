"""
GitHub Automation Engine - Core orchestration system

Enterprise-grade automation engine with intelligent decision making,
rate limiting, rollback capabilities, and comprehensive audit trails.

Building the future, one line of code at a time.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from .models import (
    GitHubIssue, GitHubAutomationAction, FeatureDetection, AutomationMetrics,
    WebhookEvent, RateLimitTracking, AutomationAction, ActionStatus, 
    ConfidenceLevel, IssueStatus
)
from .github_client import GitHubAPIClient
from .feature_detector import FeatureDetector
from .audit_logger import AuditLogger
from .rollback_manager import RollbackManager
from .rate_limiter import RateLimiter
from mcp_server.database import get_database_session
from mcp_server.config import settings

logger = structlog.get_logger()


@dataclass
class AutomationConfig:
    """Configuration for automation engine behavior."""
    # Performance settings
    max_concurrent_actions: int = 10
    batch_size: int = 50
    analysis_timeout_seconds: int = 300
    
    # Confidence thresholds
    min_confidence_auto_close: float = 0.85
    min_confidence_auto_label: float = 0.70
    min_confidence_auto_assign: float = 0.60
    
    # Rate limiting
    max_api_calls_per_hour: int = 4000  # GitHub allows 5000
    max_api_calls_per_minute: int = 60
    
    # Safety settings
    enable_rollbacks: bool = True
    require_human_approval_threshold: float = 0.50
    max_actions_per_run: int = 100
    
    # Feature flags
    enable_auto_close: bool = True
    enable_auto_label: bool = True
    enable_auto_assign: bool = False
    enable_auto_comment: bool = True
    enable_auto_milestone: bool = False


class GitHubAutomationEngine:
    """
    Core GitHub automation engine with enterprise-level capabilities.
    
    Features:
    - Intelligent issue lifecycle management
    - Feature completion detection and correlation
    - Rate-limited GitHub API interactions
    - Comprehensive audit trails and rollback capabilities
    - Scalable batch processing for large repositories
    - Real-time webhook processing
    """
    
    def __init__(
        self,
        github_token: str,
        config: Optional[AutomationConfig] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """Initialize automation engine with configuration."""
        self.config = config or AutomationConfig()
        self.github_client = GitHubAPIClient(github_token)
        self.feature_detector = FeatureDetector()
        self.audit_logger = AuditLogger()
        self.rollback_manager = RollbackManager()
        self.rate_limiter = RateLimiter(
            max_calls_per_hour=self.config.max_api_calls_per_hour,
            max_calls_per_minute=self.config.max_api_calls_per_minute
        )
        self.db_session = db_session
        
        # Processing state
        self.running = False
        self.current_batch_id: Optional[str] = None
        self.performance_metrics = {
            'total_processed': 0,
            'successful_actions': 0,
            'failed_actions': 0,
            'average_processing_time_ms': 0.0,
            'api_calls_made': 0,
            'rate_limit_hits': 0
        }
        
        logger.info(
            "GitHub Automation Engine initialized",
            config=self.config.__dict__,
            max_concurrent_actions=self.config.max_concurrent_actions
        )
    
    async def start_automation_cycle(
        self,
        repository_owner: str,
        repository_name: str,
        force_full_scan: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a complete automation cycle for a repository.
        
        Returns comprehensive results including metrics and action summaries.
        """
        start_time = time.time()
        cycle_id = f"cycle_{int(start_time)}"
        
        logger.info(
            "Starting automation cycle",
            cycle_id=cycle_id,
            repository=f"{repository_owner}/{repository_name}",
            force_full_scan=force_full_scan
        )
        
        try:
            self.running = True
            self.current_batch_id = cycle_id
            
            # Step 1: Sync issues from GitHub
            sync_results = await self._sync_issues_from_github(
                repository_owner, repository_name, force_full_scan
            )
            
            # Step 2: Analyze feature completions
            analysis_results = await self._analyze_feature_completions(
                repository_owner, repository_name
            )
            
            # Step 3: Generate automation actions
            action_results = await self._generate_automation_actions(
                repository_owner, repository_name
            )
            
            # Step 4: Execute high-confidence actions
            execution_results = await self._execute_automation_actions(
                repository_owner, repository_name
            )
            
            # Step 5: Update metrics
            await self._update_automation_metrics(
                repository_owner, repository_name, start_time
            )
            
            cycle_duration = time.time() - start_time
            
            results = {
                'cycle_id': cycle_id,
                'duration_seconds': cycle_duration,
                'repository': f"{repository_owner}/{repository_name}",
                'sync_results': sync_results,
                'analysis_results': analysis_results,
                'action_results': action_results,
                'execution_results': execution_results,
                'performance_metrics': self.performance_metrics.copy()
            }
            
            logger.info(
                "Automation cycle completed successfully",
                cycle_id=cycle_id,
                duration_seconds=cycle_duration,
                total_actions=execution_results.get('total_actions', 0),
                successful_actions=execution_results.get('successful_actions', 0)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Automation cycle failed",
                cycle_id=cycle_id,
                error=str(e),
                exc_info=True
            )
            raise
        finally:
            self.running = False
            self.current_batch_id = None
    
    async def _sync_issues_from_github(
        self,
        repository_owner: str,
        repository_name: str,
        force_full_scan: bool = False
    ) -> Dict[str, Any]:
        """Sync issues from GitHub API with rate limiting and incremental updates."""
        logger.info("Syncing issues from GitHub", repository=f"{repository_owner}/{repository_name}")
        
        sync_start = time.time()
        
        # Determine sync strategy
        last_sync_time = None
        if not force_full_scan:
            last_sync_time = await self._get_last_sync_time(repository_owner, repository_name)
        
        # Fetch issues from GitHub with pagination
        issues = await self.github_client.get_repository_issues(
            repository_owner,
            repository_name,
            since=last_sync_time,
            state="all",  # Get both open and closed
            per_page=100
        )
        
        # Process issues in batches
        new_issues = 0
        updated_issues = 0
        
        for issue_batch in self._batch_items(issues, self.config.batch_size):
            batch_results = await self._process_issue_batch(
                issue_batch, repository_owner, repository_name
            )
            new_issues += batch_results['new_issues']
            updated_issues += batch_results['updated_issues']
        
        sync_duration = time.time() - sync_start
        
        results = {
            'total_issues_fetched': len(issues),
            'new_issues': new_issues,
            'updated_issues': updated_issues,
            'sync_duration_seconds': sync_duration,
            'api_calls_made': len(issues) // 100 + 1  # Pagination estimate
        }
        
        logger.info("Issue sync completed", **results)
        return results
    
    async def _process_issue_batch(
        self,
        issues: List[Dict],
        repository_owner: str,
        repository_name: str
    ) -> Dict[str, int]:
        """Process a batch of issues for database storage."""
        new_issues = 0
        updated_issues = 0
        
        async with get_database_session() as session:
            for issue_data in issues:
                # Check if issue already exists
                existing_issue = await session.execute(
                    select(GitHubIssue).where(
                        GitHubIssue.github_issue_id == issue_data['id']
                    )
                )
                existing_issue = existing_issue.scalar_one_or_none()
                
                if existing_issue:
                    # Update existing issue
                    await self._update_existing_issue(existing_issue, issue_data, session)
                    updated_issues += 1
                else:
                    # Create new issue
                    await self._create_new_issue(issue_data, repository_owner, repository_name, session)
                    new_issues += 1
            
            await session.commit()
        
        return {'new_issues': new_issues, 'updated_issues': updated_issues}
    
    async def _analyze_feature_completions(
        self,
        repository_owner: str,
        repository_name: str
    ) -> Dict[str, Any]:
        """Analyze repository for feature completions and correlate with issues."""
        logger.info("Analyzing feature completions", repository=f"{repository_owner}/{repository_name}")
        
        analysis_start = time.time()
        
        # Get all open issues for this repository
        async with get_database_session() as session:
            result = await session.execute(
                select(GitHubIssue).where(
                    and_(
                        GitHubIssue.repository_owner == repository_owner,
                        GitHubIssue.repository_name == repository_name,
                        GitHubIssue.status == IssueStatus.OPEN
                    )
                )
            )
            open_issues = result.scalars().all()
        
        # Analyze each issue for feature completion
        analysis_results = {
            'total_issues_analyzed': len(open_issues),
            'features_detected': 0,
            'high_confidence_completions': 0,
            'completion_correlations': []
        }
        
        for issue in open_issues:
            feature_analysis = await self.feature_detector.analyze_issue_completion(
                issue, repository_owner, repository_name
            )
            
            if feature_analysis['features_detected'] > 0:
                analysis_results['features_detected'] += feature_analysis['features_detected']
                
                # Store feature detection results
                await self._store_feature_detection(issue.id, feature_analysis)
                
                # Check for high confidence completions
                for detection in feature_analysis['detections']:
                    if detection['confidence_score'] >= self.config.min_confidence_auto_close:
                        analysis_results['high_confidence_completions'] += 1
                        analysis_results['completion_correlations'].append({
                            'issue_number': issue.github_issue_number,
                            'issue_title': issue.title,
                            'feature_name': detection['feature_name'],
                            'confidence_score': detection['confidence_score'],
                            'evidence': detection['evidence']
                        })
        
        analysis_duration = time.time() - analysis_start
        analysis_results['analysis_duration_seconds'] = analysis_duration
        
        logger.info("Feature completion analysis completed", **analysis_results)
        return analysis_results
    
    async def _generate_automation_actions(
        self,
        repository_owner: str,
        repository_name: str
    ) -> Dict[str, Any]:
        """Generate automation actions based on feature analysis."""
        logger.info("Generating automation actions", repository=f"{repository_owner}/{repository_name}")
        
        # Get issues with recent feature detections
        async with get_database_session() as session:
            # Find issues with high-confidence feature completions
            high_confidence_query = select(GitHubIssue).join(FeatureDetection).where(
                and_(
                    GitHubIssue.repository_owner == repository_owner,
                    GitHubIssue.repository_name == repository_name,
                    GitHubIssue.status == IssueStatus.OPEN,
                    FeatureDetection.confidence_score >= self.config.min_confidence_auto_close,
                    FeatureDetection.completion_status == 'completed'
                )
            )
            result = await session.execute(high_confidence_query)
            high_confidence_issues = result.scalars().all()
        
        actions_generated = {
            'close_actions': 0,
            'label_actions': 0,
            'comment_actions': 0,
            'total_actions': 0
        }
        
        # Generate close actions for completed features
        if self.config.enable_auto_close:
            for issue in high_confidence_issues:
                await self._create_automation_action(
                    issue.id,
                    AutomationAction.CLOSE_ISSUE,
                    confidence_score=issue.automation_confidence or 0.9,
                    reasoning=f"Feature completion detected with high confidence",
                    evidence=await self._get_issue_completion_evidence(issue.id)
                )
                actions_generated['close_actions'] += 1
        
        # Generate labeling actions
        if self.config.enable_auto_label:
            label_actions = await self._generate_labeling_actions(
                repository_owner, repository_name
            )
            actions_generated['label_actions'] = label_actions
        
        # Generate comment actions for status updates
        if self.config.enable_auto_comment:
            comment_actions = await self._generate_comment_actions(
                repository_owner, repository_name
            )
            actions_generated['comment_actions'] = comment_actions
        
        actions_generated['total_actions'] = sum(actions_generated.values())
        
        logger.info("Automation actions generated", **actions_generated)
        return actions_generated
    
    async def _execute_automation_actions(
        self,
        repository_owner: str,
        repository_name: str
    ) -> Dict[str, Any]:
        """Execute pending automation actions with rate limiting."""
        logger.info("Executing automation actions", repository=f"{repository_owner}/{repository_name}")
        
        # Get pending actions ordered by confidence score
        async with get_database_session() as session:
            pending_actions_query = (
                select(GitHubAutomationAction)
                .join(GitHubIssue)
                .where(
                    and_(
                        GitHubIssue.repository_owner == repository_owner,
                        GitHubIssue.repository_name == repository_name,
                        GitHubAutomationAction.status == ActionStatus.PENDING,
                        GitHubAutomationAction.execution_attempts < GitHubAutomationAction.max_attempts
                    )
                )
                .order_by(GitHubAutomationAction.confidence_score.desc())
                .limit(self.config.max_actions_per_run)
            )
            result = await session.execute(pending_actions_query)
            pending_actions = result.scalars().all()
        
        execution_results = {
            'total_actions': len(pending_actions),
            'successful_actions': 0,
            'failed_actions': 0,
            'skipped_actions': 0,
            'rate_limited_actions': 0
        }
        
        # Execute actions with concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrent_actions)
        tasks = []
        
        for action in pending_actions:
            task = self._execute_single_action(action, semaphore)
            tasks.append(task)
        
        # Wait for all actions to complete
        action_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(action_results):
            if isinstance(result, Exception):
                logger.error(f"Action execution failed", action_id=pending_actions[i].id, error=str(result))
                execution_results['failed_actions'] += 1
            elif result['success']:
                execution_results['successful_actions'] += 1
            elif result['rate_limited']:
                execution_results['rate_limited_actions'] += 1
            else:
                execution_results['failed_actions'] += 1
        
        logger.info("Automation action execution completed", **execution_results)
        return execution_results
    
    async def _execute_single_action(
        self,
        action: GitHubAutomationAction,
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """Execute a single automation action with full error handling."""
        async with semaphore:
            start_time = time.time()
            
            # Check rate limit
            if not await self.rate_limiter.can_make_request():
                logger.warning("Rate limited, skipping action", action_id=action.id)
                return {'success': False, 'rate_limited': True, 'error': 'Rate limited'}
            
            try:
                # Update action status
                async with get_database_session() as session:
                    action.status = ActionStatus.IN_PROGRESS
                    action.started_at = datetime.utcnow()
                    action.execution_attempts += 1
                    await session.commit()
                
                # Execute the action based on type
                if action.action_type == AutomationAction.CLOSE_ISSUE:
                    result = await self._execute_close_action(action)
                elif action.action_type == AutomationAction.LABEL_ISSUE:
                    result = await self._execute_label_action(action)
                elif action.action_type == AutomationAction.COMMENT_ISSUE:
                    result = await self._execute_comment_action(action)
                else:
                    result = {'success': False, 'error': f'Unsupported action type: {action.action_type}'}
                
                # Update action with results
                duration_ms = (time.time() - start_time) * 1000
                await self._update_action_results(action, result, duration_ms)
                
                # Record rate limit usage
                await self.rate_limiter.record_request()
                
                return result
                
            except Exception as e:
                logger.error("Action execution failed", action_id=action.id, error=str(e), exc_info=True)
                
                # Update action with failure
                await self._update_action_failure(action, str(e))
                
                return {'success': False, 'error': str(e), 'rate_limited': False}
    
    async def _execute_close_action(self, action: GitHubAutomationAction) -> Dict[str, Any]:
        """Execute an issue close action."""
        # Get the issue
        async with get_database_session() as session:
            issue_result = await session.execute(
                select(GitHubIssue).where(GitHubIssue.id == action.issue_id)
            )
            issue = issue_result.scalar_one()
        
        # Create closing comment
        comment_body = self._generate_close_comment(action)
        
        # Close issue via GitHub API
        github_result = await self.github_client.close_issue(
            issue.repository_owner,
            issue.repository_name,
            issue.github_issue_number,
            comment_body
        )
        
        if github_result['success']:
            # Update our database
            async with get_database_session() as session:
                issue.status = IssueStatus.CLOSED
                issue.github_closed_at = datetime.utcnow()
                await session.commit()
            
            return {
                'success': True,
                'github_response': github_result,
                'actions_taken': ['close_issue', 'add_comment']
            }
        else:
            return {
                'success': False,
                'error': github_result.get('error', 'Unknown GitHub API error'),
                'github_response': github_result
            }
    
    def _generate_close_comment(self, action: GitHubAutomationAction) -> str:
        """Generate a professional closing comment."""
        evidence = action.evidence or {}
        
        comment = f"""🤖 **Automated Issue Closure**

This issue has been automatically closed because feature completion has been detected with high confidence ({action.confidence_score:.1%}).

**Completion Evidence:**
"""
        
        if evidence.get('code_files'):
            comment += f"\n📁 **Code Implementation:** {len(evidence['code_files'])} files detected"
            for file_path in evidence['code_files'][:3]:
                comment += f"\n  - `{file_path}`"
        
        if evidence.get('test_files'):
            comment += f"\n🧪 **Test Coverage:** {len(evidence['test_files'])} test files"
        
        if evidence.get('commits'):
            comment += f"\n💻 **Recent Commits:** {len(evidence['commits'])} related commits"
            for commit in evidence['commits'][:2]:
                comment += f"\n  - {commit['message'][:60]}..."
        
        comment += f"""

**Automation Details:**
- Confidence Score: {action.confidence_score:.1%}
- Detection Method: {evidence.get('detection_method', 'Multi-factor analysis')}
- Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d')}

---
*This issue was closed by the GitHub Issue Automation System. If this was closed in error, please reopen it and add the `keep-open` label to prevent future automated closures.*

🔗 **ADHDo Project** - Building the future, one line of code at a time.
"""
        
        return comment
    
    async def process_webhook_event(
        self,
        webhook_data: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Process incoming GitHub webhook events in real-time."""
        delivery_id = headers.get('X-GitHub-Delivery', 'unknown')
        event_type = headers.get('X-GitHub-Event', 'unknown')
        
        logger.info(
            "Processing webhook event",
            delivery_id=delivery_id,
            event_type=event_type,
            action=webhook_data.get('action')
        )
        
        start_time = time.time()
        
        try:
            # Store webhook event for audit
            await self._store_webhook_event(webhook_data, headers)
            
            # Process based on event type
            if event_type == 'issues':
                result = await self._process_issues_webhook(webhook_data)
            elif event_type == 'push':
                result = await self._process_push_webhook(webhook_data)
            elif event_type == 'pull_request':
                result = await self._process_pull_request_webhook(webhook_data)
            else:
                result = {'processed': False, 'reason': f'Unsupported event type: {event_type}'}
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update webhook event with results
            await self._update_webhook_processing_results(
                delivery_id, result, processing_time
            )
            
            logger.info(
                "Webhook event processed",
                delivery_id=delivery_id,
                processing_time_ms=processing_time,
                success=result.get('processed', False)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Webhook processing failed",
                delivery_id=delivery_id,
                error=str(e),
                exc_info=True
            )
            
            # Update webhook event with error
            await self._update_webhook_processing_results(
                delivery_id, {'processed': False, 'error': str(e)}, (time.time() - start_time) * 1000
            )
            
            return {'processed': False, 'error': str(e)}
    
    async def get_automation_health(self) -> Dict[str, Any]:
        """Get comprehensive automation system health metrics."""
        async with get_database_session() as session:
            # Get recent action success rates
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            
            recent_actions_query = select(GitHubAutomationAction).where(
                GitHubAutomationAction.created_at >= twenty_four_hours_ago
            )
            result = await session.execute(recent_actions_query)
            recent_actions = result.scalars().all()
            
            # Calculate metrics
            total_actions = len(recent_actions)
            successful_actions = len([a for a in recent_actions if a.success is True])
            failed_actions = len([a for a in recent_actions if a.success is False])
            pending_actions = len([a for a in recent_actions if a.status == ActionStatus.PENDING])
            
            success_rate = (successful_actions / total_actions) if total_actions > 0 else 1.0
            
            # Get rate limit status
            rate_limit_status = await self.rate_limiter.get_status()
            
            # Get average processing times
            completed_actions = [a for a in recent_actions if a.duration_ms is not None]
            avg_processing_time = (
                sum(a.duration_ms for a in completed_actions) / len(completed_actions)
                if completed_actions else 0.0
            )
            
        health_status = {
            'status': 'healthy' if success_rate >= 0.95 else 'degraded' if success_rate >= 0.8 else 'unhealthy',
            'last_24_hours': {
                'total_actions': total_actions,
                'successful_actions': successful_actions,
                'failed_actions': failed_actions,
                'pending_actions': pending_actions,
                'success_rate': success_rate,
                'average_processing_time_ms': avg_processing_time
            },
            'rate_limiting': rate_limit_status,
            'configuration': {
                'max_concurrent_actions': self.config.max_concurrent_actions,
                'auto_close_enabled': self.config.enable_auto_close,
                'auto_label_enabled': self.config.enable_auto_label,
                'rollbacks_enabled': self.config.enable_rollbacks
            },
            'system_state': {
                'running': self.running,
                'current_batch_id': self.current_batch_id
            }
        }
        
        return health_status
    
    # Helper methods (abbreviated for space - full implementations would follow)
    async def _get_last_sync_time(self, repo_owner: str, repo_name: str) -> Optional[datetime]:
        """Get the last synchronization time for incremental updates."""
        # Implementation would query the database for the most recent sync
        pass
    
    def _batch_items(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """Split items into batches of specified size."""
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]
    
    # Additional helper methods would be implemented for:
    # - _update_existing_issue
    # - _create_new_issue  
    # - _store_feature_detection
    # - _create_automation_action
    # - _get_issue_completion_evidence
    # - _generate_labeling_actions
    # - _generate_comment_actions
    # - _execute_label_action
    # - _execute_comment_action
    # - _update_action_results
    # - _update_action_failure
    # - _store_webhook_event
    # - _process_issues_webhook
    # - _process_push_webhook
    # - _process_pull_request_webhook
    # - _update_webhook_processing_results
    # - _update_automation_metrics