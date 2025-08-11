"""
ADHD-Friendly Visual Logging System

Creates beautiful, accessible logging that helps ADHD users understand what
the system is doing without overwhelming cognitive load. Logs are designed
to be visually appealing, easy to scan, and provide just the right amount
of detail for transparency without confusion.

Key Features:
- Color-coded log levels optimized for ADHD attention
- Structured visual hierarchy with icons and spacing
- Real-time streaming to web interface
- Cognitive load indicators for each log entry
- Pattern recognition for frequently logged events
- Contextual grouping to reduce visual clutter
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import structlog
from contextlib import asynccontextmanager

# Store for real-time log streaming
log_stream_subscribers: List[asyncio.Queue] = []
log_history: List[Dict[str, Any]] = []
MAX_LOG_HISTORY = 100


class ADHDLogLevel(Enum):
    """ADHD-optimized log levels with visual characteristics."""
    TRACE = ("trace", "🔍", "#64748b", "Very detailed debugging info")
    DEBUG = ("debug", "🐛", "#6366f1", "Development debugging")
    INFO = ("info", "💡", "#10b981", "Helpful information")
    SUCCESS = ("success", "✅", "#059669", "Things working well")
    WARNING = ("warning", "⚠️", "#f59e0b", "Something to pay attention to")
    ERROR = ("error", "❌", "#ef4444", "Something went wrong")
    CRITICAL = ("critical", "🚨", "#dc2626", "Urgent attention needed")
    COGNITIVE = ("cognitive", "🧠", "#8b5cf6", "Brain processing events")
    CONTEXT = ("context", "📋", "#06b6d4", "Context building events")
    PATTERN = ("pattern", "🔄", "#ec4899", "Pattern matching events")
    MEMORY = ("memory", "💾", "#84cc16", "Memory operations")
    NUDGE = ("nudge", "📯", "#f97316", "Nudging system events")
    SAFETY = ("safety", "🛡️", "#ef4444", "Safety system events")


@dataclass
class ADHDLogEntry:
    """Individual log entry optimized for ADHD display."""
    timestamp: datetime
    level: ADHDLogLevel
    message: str
    component: str
    details: Optional[Dict[str, Any]] = None
    cognitive_load: Optional[float] = None
    duration_ms: Optional[float] = None
    user_id: Optional[str] = None
    context_id: Optional[str] = None
    processing_step: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['level'] = {
            'name': self.level.value[0],
            'icon': self.level.value[1],
            'color': self.level.value[2],
            'description': self.level.value[3]
        }
        return result


class ADHDLogger:
    """
    Beautiful, ADHD-friendly logging system with real-time UI integration.
    
    Designed specifically for neurodivergent users who benefit from:
    - Visual hierarchy and clear information architecture
    - Color coding without overwhelming the senses
    - Context grouping to reduce cognitive load
    - Pattern recognition to highlight important information
    - Real-time feedback without information overload
    """
    
    def __init__(self):
        self.base_logger = structlog.get_logger()
        self.pattern_cache: Dict[str, int] = {}
        self.context_groups: Dict[str, List[ADHDLogEntry]] = {}
        
    def log(
        self,
        level: ADHDLogLevel,
        message: str,
        component: str = "system",
        **kwargs
    ):
        """
        Create an ADHD-friendly log entry.
        
        Args:
            level: Visual log level with associated colors and icons
            message: Clear, concise message (optimized for scanning)
            component: System component (for filtering and grouping)
            **kwargs: Additional context (cognitive_load, duration_ms, etc.)
        """
        
        entry = ADHDLogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            component=component,
            **kwargs
        )
        
        # Add to history (with rotation)
        log_history.append(entry.to_dict())
        if len(log_history) > MAX_LOG_HISTORY:
            log_history.pop(0)
        
        # Stream to real-time subscribers
        self._stream_to_subscribers(entry)
        
        # Group by context for visual organization
        self._add_to_context_group(entry)
        
        # Pattern detection for frequency analysis
        self._update_patterns(entry)
        
        # Traditional logging for development
        self.base_logger.info(
            message,
            level=level.value[0],
            component=component,
            **kwargs
        )
    
    def cognitive_process(
        self,
        step: str,
        message: str,
        cognitive_load: float = 0.5,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log cognitive processing steps with visual emphasis."""
        self.log(
            ADHDLogLevel.COGNITIVE,
            f"🧠 {step}: {message}",
            component="cognitive_loop",
            cognitive_load=cognitive_load,
            duration_ms=duration_ms,
            processing_step=step,
            **kwargs
        )
    
    def context_building(
        self,
        message: str,
        contexts_count: Optional[int] = None,
        load_reduction: Optional[float] = None,
        **kwargs
    ):
        """Log context building with frame assembly details."""
        details = {}
        if contexts_count:
            details['contexts_assembled'] = contexts_count
        if load_reduction:
            details['cognitive_load_reduction'] = f"{load_reduction:.1%}"
            
        self.log(
            ADHDLogLevel.CONTEXT,
            f"📋 Context: {message}",
            component="frame_builder",
            details=details,
            **kwargs
        )
    
    def pattern_match(
        self,
        pattern: str,
        confidence: float,
        response_time_ms: float,
        **kwargs
    ):
        """Log pattern matching with performance metrics."""
        # Filter kwargs to only include valid ADHDLogEntry fields
        valid_fields = {'user_id', 'context_id', 'processing_step', 'cognitive_load'}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        self.log(
            ADHDLogLevel.PATTERN,
            f"🔄 Pattern matched: {pattern} ({confidence:.1%} confidence)",
            component="pattern_matcher",
            duration_ms=response_time_ms,
            details={
                'pattern': pattern,
                'confidence': confidence,
                'ultra_fast': response_time_ms < 10,
                # Include filtered non-field kwargs in details
                **{k: v for k, v in kwargs.items() if k not in valid_fields}
            },
            **filtered_kwargs
        )
    
    def memory_operation(
        self,
        operation: str,
        tier: str,
        message: str,
        **kwargs
    ):
        """Log memory operations with tier information."""
        tier_colors = {
            'hot': '🔥',
            'warm': '🌡️', 
            'cold': '🧊'
        }
        
        self.log(
            ADHDLogLevel.MEMORY,
            f"💾 {tier_colors.get(tier, '💾')} {tier.upper()}: {operation} - {message}",
            component="memory_system",
            details={'tier': tier, 'operation': operation},
            **kwargs
        )
    
    def nudge_event(
        self,
        nudge_type: str,
        method: str,
        success: bool,
        message: str,
        **kwargs
    ):
        """Log nudging events with delivery details."""
        status_icon = "✅" if success else "❌"
        
        self.log(
            ADHDLogLevel.NUDGE,
            f"📯 {status_icon} {nudge_type} via {method}: {message}",
            component="nudge_engine",
            details={
                'nudge_type': nudge_type,
                'delivery_method': method,
                'success': success
            },
            **kwargs
        )
    
    def safety_event(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        **kwargs
    ):
        """Log safety system events with appropriate urgency."""
        severity_icons = {
            'info': '🛡️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        
        level = ADHDLogLevel.SAFETY if severity == 'info' else ADHDLogLevel.CRITICAL
        
        self.log(
            level,
            f"{severity_icons.get(severity, '🛡️')} Safety: {event_type} - {message}",
            component="safety_monitor",
            details={'event_type': event_type, 'severity': severity},
            **kwargs
        )
    
    def success(self, message: str, **kwargs):
        """Log success events with positive reinforcement."""
        self.log(ADHDLogLevel.SUCCESS, f"✅ {message}", **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log informational events."""
        self.log(ADHDLogLevel.INFO, f"💡 {message}", **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warnings with appropriate attention level."""
        self.log(ADHDLogLevel.WARNING, f"⚠️ {message}", **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log errors with clear problem indication."""
        self.log(ADHDLogLevel.ERROR, f"❌ {message}", **kwargs)
    
    def get_log_history(
        self,
        limit: int = 50,
        component_filter: Optional[str] = None,
        level_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered log history for UI display."""
        
        filtered_logs = log_history.copy()
        
        if component_filter:
            filtered_logs = [
                log for log in filtered_logs 
                if log.get('component') == component_filter
            ]
        
        if level_filter:
            filtered_logs = [
                log for log in filtered_logs
                if log.get('level', {}).get('name') == level_filter
            ]
        
        return filtered_logs[-limit:]
    
    def get_context_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get logs grouped by context for organized display."""
        result = {}
        for context_id, entries in self.context_groups.items():
            result[context_id] = [entry.to_dict() for entry in entries[-10:]]  # Last 10 per context
        return result
    
    def get_pattern_summary(self) -> Dict[str, int]:
        """Get pattern frequency summary for insights."""
        return dict(sorted(
            self.pattern_cache.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])  # Top 10 patterns
    
    def _stream_to_subscribers(self, entry: ADHDLogEntry):
        """Stream log entry to real-time subscribers."""
        entry_dict = entry.to_dict()
        
        # Remove any subscribers with closed queues
        active_subscribers = []
        for queue in log_stream_subscribers:
            try:
                queue.put_nowait(entry_dict)
                active_subscribers.append(queue)
            except asyncio.QueueFull:
                # Skip subscriber if queue is full
                continue
            except:
                # Remove broken subscriber
                continue
        
        # Update subscriber list
        log_stream_subscribers[:] = active_subscribers
    
    def _add_to_context_group(self, entry: ADHDLogEntry):
        """Add entry to context group for organized display."""
        context_id = entry.context_id or "general"
        
        if context_id not in self.context_groups:
            self.context_groups[context_id] = []
        
        self.context_groups[context_id].append(entry)
        
        # Limit entries per context group
        if len(self.context_groups[context_id]) > 20:
            self.context_groups[context_id].pop(0)
    
    def _update_patterns(self, entry: ADHDLogEntry):
        """Update pattern frequency tracking."""
        pattern_key = f"{entry.component}:{entry.level.value[0]}"
        self.pattern_cache[pattern_key] = self.pattern_cache.get(pattern_key, 0) + 1
    
    @asynccontextmanager
    async def subscribe_to_stream(self):
        """Context manager for real-time log streaming."""
        queue = asyncio.Queue(maxsize=50)  # Limit queue size
        log_stream_subscribers.append(queue)
        
        try:
            yield queue
        finally:
            if queue in log_stream_subscribers:
                log_stream_subscribers.remove(queue)


class ADHDLogFormatter:
    """Format logs for beautiful display in web interface."""
    
    @staticmethod
    def format_for_web(log_entry: Dict[str, Any]) -> str:
        """Format log entry for web display with proper HTML/CSS."""
        
        level = log_entry.get('level', {})
        icon = level.get('icon', '💡')
        color = level.get('color', '#6b7280')
        timestamp = log_entry.get('timestamp', '')
        message = log_entry.get('message', '')
        component = log_entry.get('component', 'system')
        
        # Parse timestamp for relative display
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_ago = datetime.utcnow() - dt.replace(tzinfo=None)
            
            if time_ago.total_seconds() < 60:
                relative_time = f"{int(time_ago.total_seconds())}s ago"
            elif time_ago.total_seconds() < 3600:
                relative_time = f"{int(time_ago.total_seconds() / 60)}m ago"
            else:
                relative_time = f"{int(time_ago.total_seconds() / 3600)}h ago"
        except:
            relative_time = "now"
        
        return f"""
        <div class="adhd-log-entry" data-level="{level.get('name', 'info')}" data-component="{component}">
            <div class="log-header">
                <span class="log-icon" style="color: {color}">{icon}</span>
                <span class="log-component">{component}</span>
                <span class="log-time">{relative_time}</span>
            </div>
            <div class="log-message">{message}</div>
            {ADHDLogFormatter._format_details(log_entry.get('details', {}))}
        </div>
        """
    
    @staticmethod
    def _format_details(details: Dict[str, Any]) -> str:
        """Format additional details for display."""
        if not details:
            return ""
        
        items = []
        for key, value in details.items():
            if isinstance(value, float):
                if 0 <= value <= 1:  # Probably a percentage
                    value = f"{value:.1%}"
                else:
                    value = f"{value:.1f}"
            items.append(f"<span class='detail-item'>{key}: {value}</span>")
        
        return f"<div class='log-details'>{' • '.join(items)}</div>"


# Global ADHD-friendly logger instance
adhd_logger = ADHDLogger()

# Convenience functions for easy use
def log_cognitive_process(step: str, message: str, **kwargs):
    """Quick cognitive process logging."""
    adhd_logger.cognitive_process(step, message, **kwargs)

def log_context_building(message: str, **kwargs):
    """Quick context building logging."""
    adhd_logger.context_building(message, **kwargs)

def log_pattern_match(pattern: str, confidence: float, response_time_ms: float, **kwargs):
    """Quick pattern match logging."""
    adhd_logger.pattern_match(pattern, confidence, response_time_ms, **kwargs)

def log_memory_operation(operation: str, tier: str, message: str, **kwargs):
    """Quick memory operation logging."""
    adhd_logger.memory_operation(operation, tier, message, **kwargs)

def log_nudge_event(nudge_type: str, method: str, success: bool, message: str, **kwargs):
    """Quick nudge event logging."""
    adhd_logger.nudge_event(nudge_type, method, success, message, **kwargs)

def log_success(message: str, **kwargs):
    """Quick success logging."""
    adhd_logger.success(message, **kwargs)

def log_info(message: str, **kwargs):
    """Quick info logging."""
    adhd_logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Quick warning logging."""
    adhd_logger.warning(message, **kwargs)

def log_error(message: str, **kwargs):
    """Quick error logging."""
    adhd_logger.error(message, **kwargs)