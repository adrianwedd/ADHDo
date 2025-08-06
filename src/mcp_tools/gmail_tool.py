"""
Gmail Tool - MCP Implementation

ADHD-optimized Gmail integration for email management and context extraction.
"""

import base64
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import structlog
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from mcp_client.models import (
    Tool, ToolConfig, ToolResult, ToolError, ToolType, 
    AuthType, ToolCapability, ContextFrame
)

logger = structlog.get_logger()


class GmailTool:
    """Gmail integration tool for ADHD-optimized email management."""
    
    def __init__(self, user_id: str):
        """Initialize Gmail tool."""
        self.user_id = user_id
        self.service = None
        self.credentials = None
        
        # ADHD-specific settings
        self.batch_size = 10  # Process emails in small batches
        self.priority_keywords = [
            "urgent", "asap", "deadline", "important", "critical",
            "meeting", "interview", "call", "schedule", "reminder"
        ]
        self.task_indicators = [
            "can you", "please", "could you", "would you", "need you to",
            "action required", "todo", "task", "follow up", "complete"
        ]
    
    def get_tool_config(self) -> ToolConfig:
        """Get tool configuration for MCP registration."""
        return ToolConfig(
            tool_id="gmail",
            name="Gmail Integration",
            description="ADHD-optimized Gmail management with smart email processing, task extraction, and inbox organization.",
            tool_type=ToolType.EMAIL,
            version="1.0.0",
            auth_type=AuthType.OAUTH2,
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.SEARCH,
                ToolCapability.SUBSCRIBE
            ],
            supported_operations=[
                "get_inbox",
                "get_unread_count", 
                "search_emails",
                "get_email",
                "extract_tasks",
                "get_priority_emails",
                "send_email",
                "mark_read",
                "batch_process",
                "get_email_insights",
                "schedule_email"
            ],
            cognitive_load=0.4,  # Medium cognitive load
            adhd_friendly=True,
            focus_safe=False,  # Email can be distracting
            tags=["email", "productivity", "communication", "adhd", "gmail"],
            priority=8
        )
    
    async def initialize(self, credentials_dict: Dict[str, Any]) -> bool:
        """Initialize Gmail service with credentials."""
        try:
            # Create credentials from dict
            self.credentials = Credentials.from_authorized_user_info(credentials_dict)
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            
            # Test connection
            profile = self.service.users().getProfile(userId='me').execute()
            
            logger.info("Gmail tool initialized", 
                       user_id=self.user_id,
                       email_address=profile.get('emailAddress'))
            
            return True
            
        except Exception as e:
            logger.error("Gmail initialization failed", 
                        user_id=self.user_id, 
                        error=str(e))
            return False
    
    async def invoke(
        self,
        operation: str,
        parameters: Dict[str, Any],
        context: Optional[ContextFrame] = None
    ) -> ToolResult:
        """Invoke a Gmail operation."""
        try:
            if not self.service:
                return ToolResult(
                    success=False,
                    error="Gmail service not initialized"
                )
            
            # Route to appropriate method
            if operation == "get_inbox":
                return await self._get_inbox(parameters, context)
            elif operation == "get_unread_count":
                return await self._get_unread_count(parameters, context)
            elif operation == "search_emails":
                return await self._search_emails(parameters, context)
            elif operation == "get_email":
                return await self._get_email(parameters, context)
            elif operation == "extract_tasks":
                return await self._extract_tasks(parameters, context)
            elif operation == "get_priority_emails":
                return await self._get_priority_emails(parameters, context)
            elif operation == "send_email":
                return await self._send_email(parameters, context)
            elif operation == "mark_read":
                return await self._mark_read(parameters, context)
            elif operation == "batch_process":
                return await self._batch_process(parameters, context)
            elif operation == "get_email_insights":
                return await self._get_email_insights(parameters, context)
            elif operation == "schedule_email":
                return await self._schedule_email(parameters, context)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown operation: {operation}"
                )
            
        except Exception as e:
            logger.error("Gmail operation failed", 
                        operation=operation, 
                        error=str(e))
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    # Core Gmail Operations
    
    async def _get_inbox(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Get inbox emails with ADHD-friendly processing."""
        try:
            max_results = parameters.get('max_results', self.batch_size)
            include_read = parameters.get('include_read', False)
            
            # Build query
            query = ""
            if not include_read:
                query = "is:unread"
            
            # Get messages
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = result.get('messages', [])
            
            # Process emails with ADHD-friendly summaries
            processed_emails = []
            for message in messages[:max_results]:
                email_data = await self._get_email_summary(message['id'])
                if email_data:
                    processed_emails.append(email_data)
            
            # Sort by priority for ADHD users
            processed_emails = self._sort_by_adhd_priority(processed_emails)
            
            return ToolResult(
                success=True,
                data={
                    'emails': processed_emails,
                    'total_count': len(messages),
                    'unread_count': len([e for e in processed_emails if not e.get('read', False)]),
                    'high_priority_count': len([e for e in processed_emails if e.get('priority') == 'high'])
                },
                message=f"Retrieved {len(processed_emails)} emails with ADHD-friendly processing",
                cognitive_load_impact=0.3 + (len(processed_emails) * 0.02)
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                error=f"Gmail API error: {e.reason}"
            )
    
    async def _get_unread_count(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Get unread email count with priority breakdown."""
        try:
            # Get unread messages
            result = self.service.users().messages().list(
                userId='me',
                q='is:unread'
            ).execute()
            
            messages = result.get('messages', [])
            total_unread = len(messages)
            
            # Get priority breakdown
            high_priority = 0
            medium_priority = 0
            
            # Sample first 20 for priority analysis
            sample_size = min(20, total_unread)
            for message in messages[:sample_size]:
                email_summary = await self._get_email_summary(message['id'])
                if email_summary:
                    priority = email_summary.get('priority', 'low')
                    if priority == 'high':
                        high_priority += 1
                    elif priority == 'medium':
                        medium_priority += 1
            
            # Extrapolate for full count
            if sample_size > 0:
                high_priority = int((high_priority / sample_size) * total_unread)
                medium_priority = int((medium_priority / sample_size) * total_unread)
            
            return ToolResult(
                success=True,
                data={
                    'total_unread': total_unread,
                    'high_priority': high_priority,
                    'medium_priority': medium_priority,
                    'low_priority': total_unread - high_priority - medium_priority,
                    'adhd_recommendation': self._get_unread_recommendation(total_unread, high_priority)
                },
                cognitive_load_impact=0.1
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                error=f"Gmail API error: {e.reason}"
            )
    
    async def _search_emails(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Search emails with ADHD-optimized results."""
        try:
            query = parameters.get('query', '')
            max_results = parameters.get('max_results', self.batch_size)
            
            if not query:
                return ToolResult(
                    success=False,
                    error="Search query is required"
                )
            
            # Perform search
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = result.get('messages', [])
            
            # Process search results
            search_results = []
            for message in messages:
                email_data = await self._get_email_summary(message['id'])
                if email_data:
                    # Add search relevance
                    email_data['relevance'] = self._calculate_relevance(email_data, query)
                    search_results.append(email_data)
            
            # Sort by relevance and priority
            search_results.sort(key=lambda x: (-x.get('relevance', 0), -self._get_priority_score(x)))
            
            return ToolResult(
                success=True,
                data={
                    'results': search_results,
                    'total_found': len(messages),
                    'query': query
                },
                message=f"Found {len(search_results)} relevant emails",
                cognitive_load_impact=0.2 + (len(search_results) * 0.01)
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                error=f"Gmail API error: {e.reason}"
            )
    
    async def _extract_tasks(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Extract actionable tasks from emails."""
        try:
            email_id = parameters.get('email_id')
            max_emails = parameters.get('max_emails', 5)
            
            tasks = []
            
            if email_id:
                # Extract from specific email
                email_tasks = await self._extract_tasks_from_email(email_id)
                tasks.extend(email_tasks)
            else:
                # Extract from recent unread emails
                result = self.service.users().messages().list(
                    userId='me',
                    q='is:unread',
                    maxResults=max_emails
                ).execute()
                
                messages = result.get('messages', [])
                
                for message in messages:
                    email_tasks = await self._extract_tasks_from_email(message['id'])
                    tasks.extend(email_tasks)
            
            # Deduplicate and prioritize tasks
            tasks = self._deduplicate_tasks(tasks)
            tasks = sorted(tasks, key=lambda t: t.get('priority_score', 0), reverse=True)
            
            return ToolResult(
                success=True,
                data={
                    'tasks': tasks,
                    'total_count': len(tasks),
                    'high_priority_count': len([t for t in tasks if t.get('priority') == 'high'])
                },
                message=f"Extracted {len(tasks)} actionable tasks from emails",
                cognitive_load_impact=0.4,
                follow_up_suggested=len(tasks) > 0
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Task extraction failed: {str(e)}"
            )
    
    async def _send_email(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Send an email with ADHD-friendly compose assistance."""
        try:
            to = parameters.get('to', '')
            subject = parameters.get('subject', '')
            body = parameters.get('body', '')
            
            if not all([to, subject, body]):
                return ToolResult(
                    success=False,
                    error="Missing required parameters: to, subject, body"
                )
            
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send email
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return ToolResult(
                success=True,
                data={
                    'message_id': result['id'],
                    'thread_id': result['threadId'],
                    'sent_to': to,
                    'subject': subject
                },
                message=f"Email sent successfully to {to}",
                cognitive_load_impact=0.5
            )
            
        except HttpError as e:
            return ToolResult(
                success=False,
                error=f"Failed to send email: {e.reason}"
            )
    
    # ADHD-Specific Helper Methods
    
    async def _get_email_summary(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get ADHD-friendly email summary."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract body
            body = self._extract_email_body(message['payload'])
            
            # Calculate priority
            priority = self._calculate_email_priority(headers, body)
            
            # Extract key information
            summary = {
                'id': message_id,
                'thread_id': message['threadId'],
                'from': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'read': 'UNREAD' not in message['labelIds'],
                'priority': priority,
                'priority_score': self._get_priority_score({'priority': priority}),
                'body_preview': body[:200] + ('...' if len(body) > 200 else ''),
                'has_attachments': 'parts' in message['payload'] and len(message['payload']['parts']) > 1,
                'estimated_read_time': self._estimate_read_time(body),
                'contains_tasks': self._contains_task_indicators(body),
                'urgency_indicators': self._find_urgency_indicators(body + ' ' + headers.get('Subject', ''))
            }
            
            return summary
            
        except Exception as e:
            logger.warning("Failed to get email summary", message_id=message_id, error=str(e))
            return None
    
    def _calculate_email_priority(self, headers: Dict[str, str], body: str) -> str:
        """Calculate email priority for ADHD users."""
        priority_score = 0
        
        subject = headers.get('Subject', '').lower()
        sender = headers.get('From', '').lower()
        content = (subject + ' ' + body).lower()
        
        # High priority indicators
        for keyword in self.priority_keywords:
            if keyword in content:
                priority_score += 3
        
        # Important senders (would be user-configurable)
        important_domains = ['work.com', 'company.com']  # Placeholder
        if any(domain in sender for domain in important_domains):
            priority_score += 2
        
        # Task/action indicators
        for indicator in self.task_indicators:
            if indicator in content:
                priority_score += 2
        
        # Time sensitivity
        time_patterns = ['today', 'tomorrow', 'by eod', 'deadline', 'due']
        for pattern in time_patterns:
            if pattern in content:
                priority_score += 2
        
        # Determine priority level
        if priority_score >= 6:
            return 'high'
        elif priority_score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _sort_by_adhd_priority(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort emails by ADHD-friendly priority."""
        def priority_key(email):
            # Priority order: high -> medium -> low
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            priority_score = priority_order.get(email.get('priority', 'low'), 1)
            
            # Boost unread emails
            if not email.get('read', True):
                priority_score += 0.5
            
            # Boost emails with tasks
            if email.get('contains_tasks', False):
                priority_score += 0.3
            
            return priority_score
        
        return sorted(emails, key=priority_key, reverse=True)
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract plain text body from email payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    async def _extract_tasks_from_email(self, email_id: str) -> List[Dict[str, Any]]:
        """Extract actionable tasks from a specific email."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            body = self._extract_email_body(message['payload'])
            
            tasks = []
            
            # Look for explicit task patterns
            task_patterns = [
                r'(?i)(can you|could you|please|would you)\s+([^.!?]+)',
                r'(?i)(action required|todo|task):\s*([^.!?]+)',
                r'(?i)(need you to|please)\s+([^.!?]+)',
                r'(?i)(follow up on|complete|finish)\s+([^.!?]+)'
            ]
            
            for pattern in task_patterns:
                matches = re.findall(pattern, body)
                for match in matches:
                    task_text = match[1].strip()
                    if len(task_text) > 10:  # Filter out very short matches
                        tasks.append({
                            'task': task_text,
                            'source_email_id': email_id,
                            'subject': headers.get('Subject', ''),
                            'from': headers.get('From', ''),
                            'priority': self._calculate_task_priority(task_text, body),
                            'priority_score': self._calculate_task_priority_score(task_text),
                            'estimated_time': self._estimate_task_time(task_text),
                            'deadline_mentioned': self._extract_deadline(body)
                        })
            
            return tasks
            
        except Exception as e:
            logger.warning("Failed to extract tasks from email", 
                          email_id=email_id, error=str(e))
            return []
    
    def _get_unread_recommendation(self, total_unread: int, high_priority: int) -> str:
        """Get ADHD-friendly recommendation for unread emails."""
        if total_unread == 0:
            return "Great job! Your inbox is clear. 🎉"
        elif total_unread <= 5:
            return "Manageable inbox! Consider processing these emails now."
        elif high_priority > 0:
            return f"Focus on {high_priority} high-priority emails first, then batch process the rest."
        elif total_unread <= 20:
            return "Set a 10-minute timer to batch process these emails."
        else:
            return "Large inbox detected. Consider using filters or scheduling email processing time."
    
    def _estimate_read_time(self, text: str) -> int:
        """Estimate reading time in minutes."""
        words = len(text.split())
        # Average reading speed: 200-250 words per minute
        return max(1, words // 225)
    
    def _contains_task_indicators(self, text: str) -> bool:
        """Check if email contains task indicators."""
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self.task_indicators)
    
    def _find_urgency_indicators(self, text: str) -> List[str]:
        """Find urgency indicators in text."""
        urgency_words = ['urgent', 'asap', 'immediate', 'critical', 'deadline', 'today', 'tomorrow']
        text_lower = text.lower()
        return [word for word in urgency_words if word in text_lower]
    
    def _calculate_relevance(self, email_data: Dict[str, Any], query: str) -> float:
        """Calculate search relevance score."""
        relevance = 0.0
        query_lower = query.lower()
        
        # Subject match (highest weight)
        if query_lower in email_data.get('subject', '').lower():
            relevance += 0.5
        
        # Sender match
        if query_lower in email_data.get('from', '').lower():
            relevance += 0.3
        
        # Body preview match
        if query_lower in email_data.get('body_preview', '').lower():
            relevance += 0.2
        
        return relevance
    
    def _get_priority_score(self, email_data: Dict[str, Any]) -> float:
        """Get numeric priority score for sorting."""
        priority = email_data.get('priority', 'low')
        priority_scores = {'high': 3.0, 'medium': 2.0, 'low': 1.0}
        return priority_scores.get(priority, 1.0)
    
    def _calculate_task_priority(self, task_text: str, context: str) -> str:
        """Calculate priority of extracted task."""
        text = (task_text + ' ' + context).lower()
        
        if any(word in text for word in ['urgent', 'asap', 'critical', 'immediately']):
            return 'high'
        elif any(word in text for word in ['important', 'soon', 'today', 'deadline']):
            return 'medium'
        else:
            return 'low'
    
    def _calculate_task_priority_score(self, task_text: str) -> float:
        """Calculate numeric priority score for task."""
        priority = self._calculate_task_priority(task_text, '')
        scores = {'high': 3.0, 'medium': 2.0, 'low': 1.0}
        return scores.get(priority, 1.0)
    
    def _estimate_task_time(self, task_text: str) -> str:
        """Estimate time required for task."""
        words = len(task_text.split())
        
        # Simple heuristic based on complexity indicators
        if any(word in task_text.lower() for word in ['review', 'read', 'check']):
            return "5-15 minutes"
        elif any(word in task_text.lower() for word in ['write', 'create', 'prepare']):
            return "15-30 minutes"
        elif any(word in task_text.lower() for word in ['research', 'analyze', 'develop']):
            return "30+ minutes"
        else:
            return "10-20 minutes"
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """Extract deadline mentions from text."""
        deadline_patterns = [
            r'(?i)by\s+(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?i)due\s+(today|tomorrow|\d{1,2}/\d{1,2})',
            r'(?i)deadline[:\s]+(today|tomorrow|\d{1,2}/\d{1,2})'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _deduplicate_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tasks based on similarity."""
        unique_tasks = []
        
        for task in tasks:
            is_duplicate = False
            task_text_lower = task['task'].lower()
            
            for existing_task in unique_tasks:
                existing_text_lower = existing_task['task'].lower()
                
                # Simple similarity check
                if (task_text_lower in existing_text_lower or 
                    existing_text_lower in task_text_lower):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_tasks.append(task)
        
        return unique_tasks
    
    # Additional operations would be implemented here...
    async def _get_priority_emails(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Get high-priority emails only."""
        # Implementation would filter for high-priority emails
        pass
    
    async def _mark_read(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Mark emails as read."""
        # Implementation would mark specified emails as read
        pass
    
    async def _batch_process(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Process emails in ADHD-friendly batches."""
        # Implementation would provide guided batch processing
        pass
    
    async def _get_email_insights(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Get insights about email patterns."""
        # Implementation would analyze email patterns for ADHD insights
        pass
    
    async def _schedule_email(self, parameters: Dict[str, Any], context: Optional[ContextFrame]) -> ToolResult:
        """Schedule email to be sent later."""
        # Implementation would schedule emails for optimal ADHD timing
        pass