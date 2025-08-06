"""
Comprehensive Audit Logging System

Enterprise-grade audit logging with structured logging, compliance tracking,
and forensic analysis capabilities for GitHub automation activities.
"""

import json
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .models import (
    GitHubAutomationAction, GitHubIssue, WebhookEvent, AutomationMetrics,
    ActionStatus, AutomationAction
)

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Types of audit events."""
    AUTOMATION_ACTION = "automation_action"
    WEBHOOK_RECEIVED = "webhook_received" 
    API_CALL = "api_call"
    FEATURE_DETECTION = "feature_detection"
    RATE_LIMIT_HIT = "rate_limit_hit"
    ERROR_OCCURRED = "error_occurred"
    CONFIGURATION_CHANGE = "configuration_change"
    USER_INTERACTION = "user_interaction"
    SYSTEM_EVENT = "system_event"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event."""
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    event_id: str
    user_id: Optional[str] = None
    repository: Optional[str] = None
    issue_number: Optional[int] = None
    action_type: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = None
    before_state: Optional[Dict] = None
    after_state: Optional[Dict] = None
    success: Optional[bool] = None
    error_details: Optional[str] = None
    
    def __post_init__(self):
        """Ensure metadata is initialized."""
        if self.metadata is None:
            self.metadata = {}


class AuditLogger:
    """
    Comprehensive audit logging system with multiple output formats.
    
    Features:
    - Structured logging with consistent formats
    - Database persistence for compliance
    - Real-time event streaming
    - Forensic analysis support
    - Configurable retention policies
    """
    
    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        log_file_path: Optional[str] = None,
        enable_console_logging: bool = True,
        enable_database_logging: bool = True,
        retention_days: int = 365
    ):
        """Initialize audit logger with multiple outputs."""
        self.db_session = db_session
        self.log_file_path = Path(log_file_path) if log_file_path else None
        self.enable_console_logging = enable_console_logging
        self.enable_database_logging = enable_database_logging
        self.retention_days = retention_days
        
        # Event buffering for batch processing
        self.event_buffer: List[AuditEvent] = []
        self.buffer_size = 100
        self.last_flush_time = time.time()
        self.flush_interval = 60  # seconds
        
        # Statistics
        self.stats = {
            'total_events_logged': 0,
            'events_by_type': {},
            'events_by_severity': {},
            'database_writes': 0,
            'file_writes': 0,
            'buffer_flushes': 0,
            'errors': 0
        }
        
        # Ensure log directory exists
        if self.log_file_path:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Audit logger initialized",
            log_file_path=str(self.log_file_path) if self.log_file_path else None,
            enable_console=enable_console_logging,
            enable_database=enable_database_logging,
            retention_days=retention_days
        )
    
    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        description: str,
        **kwargs
    ) -> str:
        """Log an audit event with full context."""
        event_id = f"{event_type.value}_{int(time.time() * 1000)}"
        
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            event_id=event_id,
            description=description,
            **kwargs
        )
        
        # Update statistics
        self.stats['total_events_logged'] += 1
        self.stats['events_by_type'][event_type.value] = (
            self.stats['events_by_type'].get(event_type.value, 0) + 1
        )
        self.stats['events_by_severity'][severity.value] = (
            self.stats['events_by_severity'].get(severity.value, 0) + 1
        )
        
        # Add to buffer
        self.event_buffer.append(event)
        
        # Immediate logging for critical events
        if severity == AuditSeverity.CRITICAL:
            await self._flush_events()
        
        # Check if buffer needs flushing
        elif (len(self.event_buffer) >= self.buffer_size or
              time.time() - self.last_flush_time >= self.flush_interval):
            await self._flush_events()
        
        # Console logging
        if self.enable_console_logging:
            self._log_to_console(event)
        
        return event_id
    
    async def log_automation_action(
        self,
        action: GitHubAutomationAction,
        issue: Optional[GitHubIssue] = None,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None
    ):
        """Log automation action with full context."""
        await self.log_event(
            event_type=AuditEventType.AUTOMATION_ACTION,
            severity=AuditSeverity.MEDIUM if action.success else AuditSeverity.HIGH,
            description=f"Automation action {action.action_type.value} executed",
            user_id=None,  # System action
            repository=f"{issue.repository_owner}/{issue.repository_name}" if issue else None,
            issue_number=issue.github_issue_number if issue else None,
            action_type=action.action_type.value,
            before_state=before_state,
            after_state=after_state,
            success=action.success,
            error_details=action.error_message,
            metadata={
                'action_id': action.id,
                'confidence_score': action.confidence_score,
                'reasoning': action.reasoning,
                'execution_attempts': action.execution_attempts,
                'duration_ms': action.duration_ms,
                'github_response': action.github_response
            }
        )
    
    async def log_webhook_event(
        self,
        webhook_event: WebhookEvent,
        processing_result: Dict[str, Any]
    ):
        """Log webhook event processing."""
        await self.log_event(
            event_type=AuditEventType.WEBHOOK_RECEIVED,
            severity=AuditSeverity.LOW if processing_result.get('success') else AuditSeverity.MEDIUM,
            description=f"Webhook {webhook_event.event_type} processed",
            repository=f"{webhook_event.repository_owner}/{webhook_event.repository_name}",
            success=processing_result.get('success'),
            error_details=processing_result.get('error'),
            metadata={
                'delivery_id': webhook_event.github_delivery_id,
                'event_type': webhook_event.event_type,
                'action': webhook_event.action,
                'processing_duration_ms': webhook_event.processing_duration_ms,
                'triggered_actions': webhook_event.triggered_actions,
                'automation_results': webhook_event.automation_results
            }
        )
    
    async def log_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        rate_limit_remaining: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Log GitHub API call details."""
        severity = AuditSeverity.LOW
        if status_code >= 400:
            severity = AuditSeverity.MEDIUM if status_code < 500 else AuditSeverity.HIGH
        elif rate_limit_remaining and rate_limit_remaining < 100:
            severity = AuditSeverity.MEDIUM
        
        await self.log_event(
            event_type=AuditEventType.API_CALL,
            severity=severity,
            description=f"GitHub API call: {method} {endpoint}",
            success=status_code < 400,
            error_details=error,
            metadata={
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time_ms': response_time_ms,
                'rate_limit_remaining': rate_limit_remaining
            }
        )
    
    async def log_feature_detection(
        self,
        repository: str,
        issue_number: int,
        feature_name: str,
        confidence_score: float,
        detection_result: Dict[str, Any]
    ):
        """Log feature detection results."""
        severity = AuditSeverity.LOW
        if confidence_score >= 0.9:
            severity = AuditSeverity.MEDIUM  # High confidence detections are notable
        
        await self.log_event(
            event_type=AuditEventType.FEATURE_DETECTION,
            severity=severity,
            description=f"Feature detection: {feature_name}",
            repository=repository,
            issue_number=issue_number,
            metadata={
                'feature_name': feature_name,
                'confidence_score': confidence_score,
                'detection_method': detection_result.get('detection_method'),
                'evidence': detection_result.get('evidence'),
                'completion_status': detection_result.get('completion_status')
            }
        )
    
    async def log_rate_limit_hit(
        self,
        endpoint: str,
        remaining: int,
        reset_time: datetime,
        wait_time_seconds: float
    ):
        """Log rate limit hits for monitoring."""
        await self.log_event(
            event_type=AuditEventType.RATE_LIMIT_HIT,
            severity=AuditSeverity.HIGH if wait_time_seconds > 60 else AuditSeverity.MEDIUM,
            description=f"Rate limit hit for {endpoint}",
            metadata={
                'endpoint': endpoint,
                'remaining': remaining,
                'reset_time': reset_time.isoformat(),
                'wait_time_seconds': wait_time_seconds
            }
        )
    
    async def log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        severity: AuditSeverity = AuditSeverity.HIGH
    ):
        """Log errors with full context for debugging."""
        await self.log_event(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=severity,
            description=f"Error: {str(error)}",
            success=False,
            error_details=str(error),
            metadata={
                'error_type': type(error).__name__,
                'context': context,
                'traceback': getattr(error, '__traceback__', None) and str(error.__traceback__)
            }
        )
    
    async def log_configuration_change(
        self,
        component: str,
        changed_settings: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Log configuration changes for compliance."""
        await self.log_event(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.HIGH,
            description=f"Configuration changed: {component}",
            user_id=user_id,
            metadata={
                'component': component,
                'changed_settings': changed_settings
            }
        )
    
    async def log_user_interaction(
        self,
        user_id: str,
        action: str,
        resource: str,
        success: bool = True,
        details: Optional[Dict] = None
    ):
        """Log user interactions for audit trail."""
        await self.log_event(
            event_type=AuditEventType.USER_INTERACTION,
            severity=AuditSeverity.LOW,
            description=f"User action: {action} on {resource}",
            user_id=user_id,
            success=success,
            metadata={
                'action': action,
                'resource': resource,
                'details': details or {}
            }
        )
    
    async def _flush_events(self):
        """Flush buffered events to persistent storage."""
        if not self.event_buffer:
            return
        
        events_to_flush = self.event_buffer.copy()
        self.event_buffer.clear()
        self.last_flush_time = time.time()
        self.stats['buffer_flushes'] += 1
        
        try:
            # Write to database
            if self.enable_database_logging:
                await self._write_to_database(events_to_flush)
            
            # Write to file
            if self.log_file_path:
                await self._write_to_file(events_to_flush)
            
            logger.debug(f"Flushed {len(events_to_flush)} audit events")
            
        except Exception as e:
            logger.error(f"Failed to flush audit events: {str(e)}")
            self.stats['errors'] += 1
            
            # Re-add events to buffer for retry
            self.event_buffer.extend(events_to_flush)
    
    async def _write_to_database(self, events: List[AuditEvent]):
        """Write events to database."""
        if not self.db_session:
            return
        
        try:
            # In production, this would create audit log database records
            # For now, we'll log the key details
            for event in events:
                logger.debug(
                    "Database audit log",
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    severity=event.severity.value,
                    description=event.description,
                    success=event.success
                )
            
            self.stats['database_writes'] += len(events)
            
        except Exception as e:
            logger.error(f"Failed to write audit events to database: {str(e)}")
            raise
    
    async def _write_to_file(self, events: List[AuditEvent]):
        """Write events to log file in JSON Lines format."""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                for event in events:
                    event_dict = asdict(event)
                    event_dict['timestamp'] = event.timestamp.isoformat()
                    f.write(json.dumps(event_dict, default=str) + '\n')
            
            self.stats['file_writes'] += len(events)
            
        except Exception as e:
            logger.error(f"Failed to write audit events to file: {str(e)}")
            raise
    
    def _log_to_console(self, event: AuditEvent):
        """Log event to console with structured formatting."""
        log_method = logger.info
        if event.severity == AuditSeverity.HIGH:
            log_method = logger.warning
        elif event.severity == AuditSeverity.CRITICAL:
            log_method = logger.error
        
        log_method(
            "Audit Event",
            event_id=event.event_id,
            event_type=event.event_type.value,
            severity=event.severity.value,
            description=event.description,
            repository=event.repository,
            success=event.success,
            metadata=event.metadata
        )
    
    async def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        repository: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit events with filtering."""
        # In production, this would query the database
        # For now, return recent events from buffer
        filtered_events = []
        
        for event in self.event_buffer[-limit:]:
            if event_type and event.event_type != event_type:
                continue
            if severity and event.severity != severity:
                continue
            if repository and event.repository != repository:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            filtered_events.append(asdict(event))
        
        return filtered_events
    
    async def get_audit_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get audit summary for the specified time period."""
        # In production, this would query the database for aggregated stats
        return {
            'time_period_hours': hours,
            'total_events': self.stats['total_events_logged'],
            'events_by_type': self.stats['events_by_type'].copy(),
            'events_by_severity': self.stats['events_by_severity'].copy(),
            'database_writes': self.stats['database_writes'],
            'file_writes': self.stats['file_writes'],
            'buffer_flushes': self.stats['buffer_flushes'],
            'errors': self.stats['errors'],
            'current_buffer_size': len(self.event_buffer)
        }
    
    async def cleanup_old_events(self, retention_days: Optional[int] = None):
        """Clean up old audit events based on retention policy."""
        if retention_days is None:
            retention_days = self.retention_days
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # In production, this would delete old records from the database
        logger.info(
            "Audit event cleanup",
            cutoff_date=cutoff_date.isoformat(),
            retention_days=retention_days
        )
    
    async def export_audit_trail(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = 'json'
    ) -> str:
        """Export audit trail for compliance reporting."""
        events = await self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if format == 'json':
            return json.dumps(events, indent=2, default=str)
        elif format == 'csv':
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].keys())
                writer.writeheader()
                writer.writerows(events)
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit logger statistics."""
        return self.stats.copy()
    
    async def force_flush(self):
        """Force flush of all buffered events."""
        await self._flush_events()
    
    async def close(self):
        """Close audit logger and flush remaining events."""
        await self._flush_events()
        logger.info("Audit logger closed", final_statistics=self.stats)