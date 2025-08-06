"""
Rollback Manager for Safe Automation Operations

Enterprise-grade rollback system with transaction management, state tracking,
and automated recovery for GitHub automation actions.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .models import (
    GitHubAutomationAction, GitHubIssue, ActionStatus, AutomationAction
)
from .github_client import GitHubAPIClient
from .audit_logger import AuditLogger, AuditEventType, AuditSeverity

logger = structlog.get_logger()


class RollbackStatus(str, Enum):
    """Rollback operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class RollbackReason(str, Enum):
    """Reasons for rollback operations."""
    USER_REQUEST = "user_request"
    ERROR_DETECTED = "error_detected"
    POLICY_VIOLATION = "policy_violation"
    SYSTEM_FAILURE = "system_failure"
    AUTOMATED_SAFETY = "automated_safety"
    COMPLIANCE_REQUIREMENT = "compliance_requirement"


@dataclass
class RollbackOperation:
    """Individual rollback operation definition."""
    operation_id: str
    action_id: str
    rollback_type: str
    rollback_data: Dict[str, Any]
    status: RollbackStatus = RollbackStatus.PENDING
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class RollbackTransaction:
    """Rollback transaction containing multiple operations."""
    transaction_id: str
    reason: RollbackReason
    operations: List[RollbackOperation]
    status: RollbackStatus = RollbackStatus.PENDING
    created_by: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class RollbackManager:
    """
    Comprehensive rollback management system for GitHub automation.
    
    Features:
    - Transactional rollback operations
    - State preservation and restoration
    - Automated safety checks
    - Partial rollback support
    - Comprehensive audit trails
    """
    
    def __init__(
        self,
        github_client: Optional[GitHubAPIClient] = None,
        audit_logger: Optional[AuditLogger] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """Initialize rollback manager."""
        self.github_client = github_client
        self.audit_logger = audit_logger
        self.db_session = db_session
        
        # Active transactions
        self.active_transactions: Dict[str, RollbackTransaction] = {}
        
        # Rollback handlers for different action types
        self.rollback_handlers: Dict[AutomationAction, Callable] = {}
        
        # Statistics
        self.stats = {
            'total_rollbacks': 0,
            'successful_rollbacks': 0,
            'failed_rollbacks': 0,
            'partial_rollbacks': 0,
            'rollbacks_by_reason': {},
            'average_rollback_time_ms': 0.0
        }
        
        # Register default rollback handlers
        self._register_default_handlers()
        
        logger.info(
            "Rollback manager initialized",
            has_github_client=bool(github_client),
            has_audit_logger=bool(audit_logger)
        )
    
    def _register_default_handlers(self):
        """Register default rollback handlers for each action type."""
        self.rollback_handlers = {
            AutomationAction.CLOSE_ISSUE: self._rollback_close_issue,
            AutomationAction.UPDATE_ISSUE: self._rollback_update_issue,
            AutomationAction.LABEL_ISSUE: self._rollback_label_issue,
            AutomationAction.ASSIGN_ISSUE: self._rollback_assign_issue,
            AutomationAction.COMMENT_ISSUE: self._rollback_comment_issue,
            AutomationAction.MILESTONE_ISSUE: self._rollback_milestone_issue
        }
    
    async def create_rollback_transaction(
        self,
        action_ids: List[str],
        reason: RollbackReason,
        created_by: Optional[str] = None
    ) -> str:
        """
        Create a rollback transaction for multiple actions.
        
        Args:
            action_ids: List of automation action IDs to rollback
            reason: Reason for the rollback
            created_by: User or system initiating the rollback
            
        Returns:
            Transaction ID for tracking
        """
        transaction_id = str(uuid4())
        
        logger.info(
            "Creating rollback transaction",
            transaction_id=transaction_id,
            action_count=len(action_ids),
            reason=reason.value,
            created_by=created_by
        )
        
        # Fetch actions from database
        operations = []
        
        if self.db_session:
            async with self.db_session() as session:
                for action_id in action_ids:
                    result = await session.execute(
                        select(GitHubAutomationAction).where(
                            GitHubAutomationAction.id == action_id
                        )
                    )
                    action = result.scalar_one_or_none()
                    
                    if action and action.rollback_data and action.can_rollback:
                        operation = RollbackOperation(
                            operation_id=str(uuid4()),
                            action_id=action_id,
                            rollback_type=action.action_type.value,
                            rollback_data=action.rollback_data
                        )
                        operations.append(operation)
                    else:
                        logger.warning(
                            "Action cannot be rolled back",
                            action_id=action_id,
                            has_rollback_data=bool(action and action.rollback_data),
                            can_rollback=bool(action and action.can_rollback)
                        )
        
        # Create transaction
        transaction = RollbackTransaction(
            transaction_id=transaction_id,
            reason=reason,
            operations=operations,
            created_by=created_by
        )
        
        self.active_transactions[transaction_id] = transaction
        
        # Log to audit trail
        if self.audit_logger:
            await self.audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_EVENT,
                severity=AuditSeverity.HIGH,
                description=f"Rollback transaction created: {reason.value}",
                user_id=created_by,
                metadata={
                    'transaction_id': transaction_id,
                    'action_count': len(action_ids),
                    'operation_count': len(operations),
                    'reason': reason.value
                }
            )
        
        return transaction_id
    
    async def execute_rollback_transaction(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        """
        Execute a rollback transaction.
        
        Returns detailed results of the rollback operation.
        """
        if transaction_id not in self.active_transactions:
            raise ValueError(f"Rollback transaction {transaction_id} not found")
        
        transaction = self.active_transactions[transaction_id]
        start_time = time.time()
        
        logger.info(
            "Executing rollback transaction",
            transaction_id=transaction_id,
            operation_count=len(transaction.operations)
        )
        
        transaction.status = RollbackStatus.IN_PROGRESS
        results = {
            'transaction_id': transaction_id,
            'total_operations': len(transaction.operations),
            'successful_operations': 0,
            'failed_operations': 0,
            'operation_results': [],
            'overall_status': RollbackStatus.IN_PROGRESS,
            'start_time': datetime.utcnow().isoformat(),
            'duration_ms': 0
        }
        
        try:
            # Execute each rollback operation
            for operation in transaction.operations:
                operation_result = await self._execute_rollback_operation(operation)
                results['operation_results'].append(operation_result)
                
                if operation_result['success']:
                    results['successful_operations'] += 1
                else:
                    results['failed_operations'] += 1
            
            # Determine overall status
            if results['failed_operations'] == 0:
                transaction.status = RollbackStatus.COMPLETED
                results['overall_status'] = RollbackStatus.COMPLETED
                self.stats['successful_rollbacks'] += 1
            elif results['successful_operations'] > 0:
                transaction.status = RollbackStatus.PARTIALLY_COMPLETED
                results['overall_status'] = RollbackStatus.PARTIALLY_COMPLETED
                self.stats['partial_rollbacks'] += 1
            else:
                transaction.status = RollbackStatus.FAILED
                results['overall_status'] = RollbackStatus.FAILED
                self.stats['failed_rollbacks'] += 1
            
            transaction.completed_at = datetime.utcnow()
            
        except Exception as e:
            transaction.status = RollbackStatus.FAILED
            results['overall_status'] = RollbackStatus.FAILED
            results['error'] = str(e)
            self.stats['failed_rollbacks'] += 1
            
            logger.error(
                "Rollback transaction failed",
                transaction_id=transaction_id,
                error=str(e),
                exc_info=True
            )
        
        finally:
            duration_ms = (time.time() - start_time) * 1000
            results['duration_ms'] = duration_ms
            results['completed_at'] = datetime.utcnow().isoformat()
            
            # Update statistics
            self.stats['total_rollbacks'] += 1
            reason_count = self.stats['rollbacks_by_reason'].get(transaction.reason.value, 0)
            self.stats['rollbacks_by_reason'][transaction.reason.value] = reason_count + 1
            
            # Update average rollback time
            current_avg = self.stats['average_rollback_time_ms']
            total_rollbacks = self.stats['total_rollbacks']
            self.stats['average_rollback_time_ms'] = (
                (current_avg * (total_rollbacks - 1) + duration_ms) / total_rollbacks
            )
            
            # Log completion
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type=AuditEventType.SYSTEM_EVENT,
                    severity=AuditSeverity.HIGH if transaction.status == RollbackStatus.FAILED else AuditSeverity.MEDIUM,
                    description=f"Rollback transaction {transaction.status.value}",
                    user_id=transaction.created_by,
                    success=transaction.status in [RollbackStatus.COMPLETED, RollbackStatus.PARTIALLY_COMPLETED],
                    metadata={
                        'transaction_id': transaction_id,
                        'duration_ms': duration_ms,
                        'successful_operations': results['successful_operations'],
                        'failed_operations': results['failed_operations']
                    }
                )
        
        return results
    
    async def _execute_rollback_operation(
        self,
        operation: RollbackOperation
    ) -> Dict[str, Any]:
        """Execute a single rollback operation."""
        operation.status = RollbackStatus.IN_PROGRESS
        operation.attempts += 1
        start_time = time.time()
        
        logger.debug(
            "Executing rollback operation",
            operation_id=operation.operation_id,
            action_id=operation.action_id,
            rollback_type=operation.rollback_type
        )
        
        try:
            # Get the appropriate rollback handler
            action_type = AutomationAction(operation.rollback_type)
            handler = self.rollback_handlers.get(action_type)
            
            if not handler:
                raise ValueError(f"No rollback handler for action type: {action_type}")
            
            # Execute the rollback
            rollback_result = await handler(operation.rollback_data)
            
            if rollback_result.get('success', False):
                operation.status = RollbackStatus.COMPLETED
                operation.completed_at = datetime.utcnow()
                
                # Mark original action as rolled back
                await self._mark_action_rolled_back(
                    operation.action_id, 
                    f"Rolled back successfully: {rollback_result.get('message', '')}"
                )
                
                return {
                    'operation_id': operation.operation_id,
                    'action_id': operation.action_id,
                    'success': True,
                    'duration_ms': (time.time() - start_time) * 1000,
                    'result': rollback_result
                }
            else:
                operation.status = RollbackStatus.FAILED
                operation.error_message = rollback_result.get('error', 'Unknown error')
                
                return {
                    'operation_id': operation.operation_id,
                    'action_id': operation.action_id,
                    'success': False,
                    'duration_ms': (time.time() - start_time) * 1000,
                    'error': operation.error_message
                }
        
        except Exception as e:
            operation.status = RollbackStatus.FAILED
            operation.error_message = str(e)
            
            logger.error(
                "Rollback operation failed",
                operation_id=operation.operation_id,
                action_id=operation.action_id,
                error=str(e),
                exc_info=True
            )
            
            return {
                'operation_id': operation.operation_id,
                'action_id': operation.action_id,
                'success': False,
                'duration_ms': (time.time() - start_time) * 1000,
                'error': str(e)
            }
    
    async def _mark_action_rolled_back(self, action_id: str, reason: str):
        """Mark an automation action as rolled back in the database."""
        if not self.db_session:
            return
        
        try:
            async with self.db_session() as session:
                result = await session.execute(
                    select(GitHubAutomationAction).where(
                        GitHubAutomationAction.id == action_id
                    )
                )
                action = result.scalar_one_or_none()
                
                if action:
                    action.status = ActionStatus.ROLLED_BACK
                    action.rolled_back = True
                    action.rollback_reason = reason
                    await session.commit()
                    
                    logger.info(
                        "Action marked as rolled back",
                        action_id=action_id,
                        reason=reason
                    )
        
        except Exception as e:
            logger.error(f"Failed to mark action as rolled back: {str(e)}")
    
    # Rollback Handlers for Different Action Types
    
    async def _rollback_close_issue(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback issue closure by reopening the issue."""
        try:
            owner = rollback_data['repository_owner']
            repo = rollback_data['repository_name']
            issue_number = rollback_data['issue_number']
            
            if not self.github_client:
                return {'success': False, 'error': 'No GitHub client available'}
            
            # Reopen the issue
            result = await self.github_client._make_request(
                'PATCH',
                f'/repos/{owner}/{repo}/issues/{issue_number}',
                json_data={'state': 'open'}
            )
            
            if result['success']:
                # Add rollback comment
                comment = (
                    "🔄 **Issue Reopened - Automation Rollback**\\n\\n"
                    "This issue has been automatically reopened due to a rollback of "
                    "the previous automated closure.\\n\\n"
                    f"Rollback performed at: {datetime.utcnow().isoformat()}\\n\\n"
                    "*If this issue should remain closed, please close it manually.*"
                )
                
                await self.github_client.create_issue_comment(
                    owner, repo, issue_number, comment
                )
                
                return {
                    'success': True,
                    'message': f'Issue #{issue_number} reopened successfully',
                    'github_response': result
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to reopen issue')
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _rollback_update_issue(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback issue update by restoring previous state."""
        try:
            owner = rollback_data['repository_owner']
            repo = rollback_data['repository_name']
            issue_number = rollback_data['issue_number']
            previous_state = rollback_data['previous_state']
            
            if not self.github_client:
                return {'success': False, 'error': 'No GitHub client available'}
            
            # Restore previous issue state
            result = await self.github_client._make_request(
                'PATCH',
                f'/repos/{owner}/{repo}/issues/{issue_number}',
                json_data=previous_state
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Issue #{issue_number} state restored successfully',
                    'github_response': result
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to restore issue state')
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _rollback_label_issue(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback issue labeling by restoring previous labels."""
        try:
            owner = rollback_data['repository_owner']
            repo = rollback_data['repository_name']
            issue_number = rollback_data['issue_number']
            previous_labels = rollback_data.get('previous_labels', [])
            
            if not self.github_client:
                return {'success': False, 'error': 'No GitHub client available'}
            
            # Restore previous labels
            result = await self.github_client.update_issue_labels(
                owner, repo, issue_number, previous_labels
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Issue #{issue_number} labels restored successfully',
                    'restored_labels': previous_labels
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to restore labels')
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _rollback_assign_issue(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback issue assignment by restoring previous assignees."""
        try:
            owner = rollback_data['repository_owner']
            repo = rollback_data['repository_name']
            issue_number = rollback_data['issue_number']
            previous_assignees = rollback_data.get('previous_assignees', [])
            
            if not self.github_client:
                return {'success': False, 'error': 'No GitHub client available'}
            
            # Restore previous assignees
            result = await self.github_client._make_request(
                'PATCH',
                f'/repos/{owner}/{repo}/issues/{issue_number}',
                json_data={'assignees': previous_assignees}
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Issue #{issue_number} assignees restored successfully',
                    'restored_assignees': previous_assignees
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to restore assignees')
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _rollback_comment_issue(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback issue comment by deleting the added comment."""
        try:
            owner = rollback_data['repository_owner']
            repo = rollback_data['repository_name']
            comment_id = rollback_data.get('comment_id')
            
            if not self.github_client:
                return {'success': False, 'error': 'No GitHub client available'}
            
            if not comment_id:
                return {'success': False, 'error': 'No comment ID provided for rollback'}
            
            # Delete the comment
            result = await self.github_client._make_request(
                'DELETE',
                f'/repos/{owner}/{repo}/issues/comments/{comment_id}'
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Comment {comment_id} deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to delete comment')
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _rollback_milestone_issue(self, rollback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback milestone assignment by restoring previous milestone."""
        try:
            owner = rollback_data['repository_owner']
            repo = rollback_data['repository_name']
            issue_number = rollback_data['issue_number']
            previous_milestone = rollback_data.get('previous_milestone')
            
            if not self.github_client:
                return {'success': False, 'error': 'No GitHub client available'}
            
            # Restore previous milestone
            result = await self.github_client._make_request(
                'PATCH',
                f'/repos/{owner}/{repo}/issues/{issue_number}',
                json_data={'milestone': previous_milestone}
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Issue #{issue_number} milestone restored successfully',
                    'restored_milestone': previous_milestone
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to restore milestone')
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def can_rollback_action(self, action_id: str) -> bool:
        """Check if an action can be rolled back."""
        if not self.db_session:
            return False
        
        try:
            async with self.db_session() as session:
                result = await session.execute(
                    select(GitHubAutomationAction).where(
                        GitHubAutomationAction.id == action_id
                    )
                )
                action = result.scalar_one_or_none()
                
                return (
                    action is not None and
                    action.can_rollback and
                    not action.rolled_back and
                    action.rollback_data is not None and
                    action.success is True  # Only rollback successful actions
                )
        
        except Exception as e:
            logger.error(f"Error checking rollback capability: {str(e)}")
            return False
    
    async def get_rollback_transaction_status(
        self,
        transaction_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the status of a rollback transaction."""
        if transaction_id not in self.active_transactions:
            return None
        
        transaction = self.active_transactions[transaction_id]
        
        return {
            'transaction_id': transaction_id,
            'status': transaction.status.value,
            'reason': transaction.reason.value,
            'created_by': transaction.created_by,
            'created_at': transaction.created_at.isoformat(),
            'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None,
            'operation_count': len(transaction.operations),
            'operations': [
                {
                    'operation_id': op.operation_id,
                    'action_id': op.action_id,
                    'rollback_type': op.rollback_type,
                    'status': op.status.value,
                    'attempts': op.attempts,
                    'error_message': op.error_message
                }
                for op in transaction.operations
            ]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rollback manager statistics."""
        return self.stats.copy()
    
    def register_rollback_handler(
        self,
        action_type: AutomationAction,
        handler: Callable
    ):
        """Register a custom rollback handler for an action type."""
        self.rollback_handlers[action_type] = handler
        logger.info(f"Registered rollback handler for {action_type.value}")
    
    async def cleanup_completed_transactions(self, hours: int = 24):
        """Clean up completed rollback transactions older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        completed_transactions = [
            tid for tid, trans in self.active_transactions.items()
            if trans.status in [RollbackStatus.COMPLETED, RollbackStatus.FAILED] and
            trans.completed_at and trans.completed_at < cutoff_time
        ]
        
        for transaction_id in completed_transactions:
            del self.active_transactions[transaction_id]
        
        logger.info(f"Cleaned up {len(completed_transactions)} completed rollback transactions")
        
        return len(completed_transactions)