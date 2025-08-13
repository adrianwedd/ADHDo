"""
Claude browser-first authentication module for cost-efficient LLM operations.

This module implements browser-first authentication for Claude, allowing the system to
use session-based authentication which is more cost-effective than API key usage
for development and medium-scale operations.
"""

import json
import asyncio
import time
import hashlib
from typing import Dict, Any, Optional, List
import httpx
from dataclasses import dataclass, asdict
import logging
from functools import wraps

# Simple config fallbacks for ADHD system
class Config:
    def __init__(self):
        import os
        self.claude_session_key = os.getenv('CLAUDE_SESSION_KEY', '')
        self.claude_org_id = os.getenv('CLAUDE_ORG_ID', '1287541f-a020-4755-bbb0-8945a1be4fa5')
        self.claude_user_id = os.getenv('CLAUDE_USER_ID', 'f71a8285-af11-4a58-ae8a-0020ecb210e8')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
        self.claude_max_tokens = int(os.getenv('CLAUDE_MAX_TOKENS', '1000'))
        self.claude_temperature = float(os.getenv('CLAUDE_TEMPERATURE', '0.7'))
        self.http_timeout = httpx.Timeout(30.0, connect=10.0)
        self.auth_strategy = 'browser_first'
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
    
    def setup_logging(self):
        return logging.getLogger(__name__)

config = Config()


class SecurityMonitor:
    """Simple security monitor stub."""
    def record_rate_limit_exceeded(self, **kwargs):
        logging.warning(f"Rate limit exceeded: {kwargs}")
    
    def record_auth_failure(self, **kwargs):
        logging.error(f"Auth failure: {kwargs}")

security_monitor = SecurityMonitor()


class ClaudeAuthError(Exception):
    """Raised when Claude authentication fails."""
    pass


class RateLimiter:
    """Rate limiter for authentication attempts to prevent abuse."""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = {}
        
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed based on rate limiting."""
        now = time.time()
        
        # Clean old attempts
        cutoff = now - self.window_seconds
        self.attempts[key] = [attempt for attempt in self.attempts.get(key, []) if attempt > cutoff]
        
        return len(self.attempts.get(key, [])) < self.max_attempts
    
    def record_attempt(self, key: str):
        """Record an authentication attempt."""
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(time.time())


def secure_log_auth_error(func):
    """Decorator to securely log authentication errors without exposing credentials."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ClaudeAuthError as e:
            # Hash any potential credential info for secure logging
            error_msg = str(e)
            if 'sk-ant-' in error_msg:
                error_msg = error_msg.replace(error_msg[error_msg.find('sk-ant-'):error_msg.find('sk-ant-')+20], 'sk-ant-***REDACTED***')
            logging.getLogger(__name__).error(f"Authentication error (sanitized): {error_msg}")
            raise
        except Exception as e:
            logging.getLogger(__name__).error(f"Unexpected auth error: {type(e).__name__}")
            raise ClaudeAuthError(f"Authentication system error: {type(e).__name__}") from e
    return wrapper


@dataclass
class ClaudeMessage:
    """Represents a message in Claude conversation."""
    role: str  # 'user' or 'assistant'
    content: str


@dataclass
class ClaudeConversation:
    """Represents a Claude conversation session."""
    conversation_id: str
    messages: List[ClaudeMessage]
    created_at: str


class ClaudeBrowserAuth:
    """
    Browser-first authentication handler for Claude API.
    
    This class handles authentication using browser session credentials,
    which provides cost efficiency compared to direct API usage.
    """
    
    def __init__(self, session_key: Optional[str] = None):
        """Initialize Claude browser authentication with security validation."""
        self.session_key = session_key or config.claude_session_key
        self.org_id = config.claude_org_id  
        self.user_id = config.claude_user_id
        self.base_url = "https://claude.ai/api"
        self.client: Optional[httpx.AsyncClient] = None
        self.logger = config.setup_logging()
        self.rate_limiter = RateLimiter(max_attempts=3, window_seconds=300)  # 3 attempts per 5 minutes
        self._auth_validated = False
        self._last_validation = 0
        self._validation_ttl = 300  # Re-validate every 5 minutes
        self._client_initialized = False  # Track if client is initialized
        
        # Comprehensive credential validation
        if self.session_key:
            self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate credential format and security requirements."""
        missing_creds = []
        
        if not self.session_key:
            missing_creds.append("CLAUDE_SESSION_KEY")
        elif not self.session_key.startswith('sk-ant-sid01-') or len(self.session_key) < 50:
            raise ClaudeAuthError("Invalid CLAUDE_SESSION_KEY format - must start with 'sk-ant-sid01-' and be sufficiently long")
        
        if not self.org_id:
            missing_creds.append("CLAUDE_ORG_ID")
        elif len(self.org_id) != 36 or self.org_id.count('-') != 4:
            raise ClaudeAuthError("Invalid CLAUDE_ORG_ID format - must be a valid UUID")
            
        if not self.user_id:
            missing_creds.append("CLAUDE_USER_ID")
        elif len(self.user_id) != 36 or self.user_id.count('-') != 4:
            raise ClaudeAuthError("Invalid CLAUDE_USER_ID format - must be a valid UUID")
            
        if missing_creds:
            raise ClaudeAuthError(
                f"Browser-first authentication missing required credentials: {', '.join(missing_creds)}. "
                "Please check your .env file and ensure all Claude authentication variables are set."
            )
        
        # Log successful credential validation (without exposing values)
        self.logger.info("Claude browser authentication credentials validated")
    
    async def __aenter__(self):
        """Async context manager entry with reuse protection."""
        if not self._client_initialized:
            await self.initialize_client()
            self._client_initialized = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Don't close immediately - leave client open for reuse
        # Only close if explicitly needed
        pass
    
    async def initialize_client(self):
        """Initialize the HTTP client with browser session credentials."""
        if self.client:
            return  # Already initialized
            
        # Create comprehensive cookie header like working CV implementation
        cookie_parts = [
            f'sessionKey={self.session_key}',
            f'lastActiveOrg={self.org_id}',
            f'ajs_user_id={self.user_id}'
        ]
        cookie_header = '; '.join(cookie_parts)
        
        headers = {
            'Cookie': cookie_header,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Referer': 'https://claude.ai/',
            'Origin': 'https://claude.ai'
        }
        
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=config.http_timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # Verify authentication
        await self.verify_authentication()
    
    @secure_log_auth_error
    async def verify_authentication(self):
        """Verify that the browser authentication is working with comprehensive error handling."""
        
        # Rate limiting check
        client_key = hashlib.sha256(f"{self.org_id}:{self.user_id}".encode()).hexdigest()[:16]
        if not self.rate_limiter.is_allowed(client_key):
            security_monitor.record_rate_limit_exceeded(
                source=f"claude_auth:{client_key}",
                attempts=len(self.rate_limiter.attempts.get(client_key, [])),
                window_seconds=self.rate_limiter.window_seconds
            )
            raise ClaudeAuthError("Rate limit exceeded for authentication attempts. Please wait before retrying.")
        
        # Check if validation is still valid (TTL-based)
        if self._auth_validated and (time.time() - self._last_validation) < self._validation_ttl:
            return
        
        self.rate_limiter.record_attempt(client_key)
        
        try:
            # Test with a simple, low-cost endpoint
            response = await self.client.get(
                f"{self.base_url}/organizations/{self.org_id}/chat_conversations",
                timeout=15.0  # Shorter timeout for auth verification
            )
            response.raise_for_status()
            
            # Verify response structure is what we expect
            try:
                data = response.json()
                if not isinstance(data, list):
                    raise ClaudeAuthError("Unexpected response format from Claude API")
            except json.JSONDecodeError:
                # Some endpoints might return non-JSON, but 200 status is still valid auth
                pass
            
            self._auth_validated = True
            self._last_validation = time.time()
            self.logger.info("Claude browser authentication verified successfully")
            
        except httpx.HTTPStatusError as e:
            self._auth_validated = False
            
            # Record authentication failure with security monitoring
            if e.response.status_code == 401:
                security_monitor.record_auth_failure(
                    source=f"claude_auth:{client_key}",
                    error_type="invalid_session_key",
                    details={"status_code": 401, "org_id": self.org_id[:8] + "..."}
                )
                raise ClaudeAuthError(
                    "Claude session key is invalid or expired. Please refresh your browser session "
                    "and update the CLAUDE_SESSION_KEY in your .env file."
                )
            elif e.response.status_code == 403:
                security_monitor.record_auth_failure(
                    source=f"claude_auth:{client_key}",
                    error_type="access_denied",
                    details={"status_code": 403, "org_id": self.org_id[:8] + "..."}
                )
                raise ClaudeAuthError(
                    "Claude organization access denied. Please verify your CLAUDE_ORG_ID and "
                    "ensure you have access to the specified organization."
                )
            elif e.response.status_code == 429:
                security_monitor.record_auth_failure(
                    source=f"claude_auth:{client_key}",
                    error_type="rate_limit_exceeded",
                    details={"status_code": 429}
                )
                raise ClaudeAuthError(
                    "Rate limit exceeded by Claude API. Please wait before retrying. "
                    "Consider implementing exponential backoff in your application."
                )
            else:
                security_monitor.record_auth_failure(
                    source=f"claude_auth:{client_key}",
                    error_type="http_error",
                    details={"status_code": e.response.status_code}
                )
                self.logger.error(f"Authentication verification failed with status {e.response.status_code}: {e.response.text[:200]}")
                raise ClaudeAuthError(f"Authentication verification failed: HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            raise ClaudeAuthError("Authentication verification timed out. Please check your network connection.")
        except httpx.ConnectError:
            raise ClaudeAuthError("Cannot connect to Claude API. Please check your internet connection.")
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication verification: {type(e).__name__}: {e}")
            raise ClaudeAuthError(f"Failed to verify Claude authentication: {type(e).__name__}")
    
    async def create_conversation(self) -> str:
        """Create a new conversation and return its ID, or use an existing one."""
        try:
            # First, try to get existing conversations
            response = await self.client.get(f"{self.base_url}/organizations/{self.org_id}/chat_conversations")
            response.raise_for_status()
            
            conversations = response.json()
            if conversations and len(conversations) > 0:
                # Use the most recent conversation
                conversation_id = conversations[0].get('uuid')
                if conversation_id:
                    self.logger.debug(f"Using existing Claude conversation: {conversation_id}")
                    return conversation_id
            
            # If no existing conversations, create a new one with minimal payload
            payload = {
                "name": ""  # Minimal payload - let Claude generate the conversation
            }
            
            response = await self.client.post(
                f"{self.base_url}/organizations/{self.org_id}/chat_conversations",
                json=payload
            )
            response.raise_for_status()
            
            conversation_data = response.json()
            conversation_id = conversation_data.get('uuid')
            
            if not conversation_id:
                raise ClaudeAuthError("Failed to create conversation: no ID returned")
            
            self.logger.debug(f"Created new Claude conversation: {conversation_id}")
            return conversation_id
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Try with empty payload as fallback
                try:
                    response = await self.client.post(
                        f"{self.base_url}/organizations/{self.org_id}/chat_conversations",
                        json={}
                    )
                    response.raise_for_status()
                    conversation_data = response.json()
                    conversation_id = conversation_data.get('uuid')
                    if conversation_id:
                        self.logger.debug(f"Created conversation with empty payload: {conversation_id}")
                        return conversation_id
                except:
                    pass
                    
            raise ClaudeAuthError(f"Failed to create conversation: HTTP {e.response.status_code}")
        except Exception as e:
            raise ClaudeAuthError(f"Failed to create conversation: {e}")
    
    @secure_log_auth_error  
    async def send_message(self, conversation_id: str, message: str, model: str = None) -> str:
        """
        Send a message to Claude and return the response.
        
        Args:
            conversation_id: The conversation ID
            message: The message to send
            model: The Claude model to use (defaults to config.claude_model)
        
        Returns:
            Claude's response text
        """
        model = model or config.claude_model
        
        try:
            payload = {
                "prompt": message,
                "timezone": "Australia/Tasmania", 
                "model": model,
                "attachments": []
            }
            
            # Update headers for this specific request
            headers = self.client.headers.copy()
            headers['Accept'] = 'text/event-stream'
            headers['Cookie'] = f'sessionKey={self.session_key}'
            
            response = await self.client.post(
                f"{self.base_url}/organizations/{self.org_id}/chat_conversations/{conversation_id}/completion",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            # Parse Claude's streaming response format
            response_text = ""
            try:
                # Claude sends Server-Sent Events (SSE) format
                response_content = response.content.decode('utf-8')
                
                # Parse each line of the SSE stream
                for line in response_content.split('\n'):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Handle SSE data lines
                    if line.startswith('data: '):
                        data_str = line[6:].strip()
                        
                        # Skip DONE marker
                        if data_str == '[DONE]':
                            break
                            
                        # Skip empty data
                        if not data_str:
                            continue
                            
                        try:
                            # Parse the JSON data
                            data = json.loads(data_str)
                            
                            # Extract text from various possible response formats
                            if isinstance(data, dict):
                                # Try common field names for Claude responses
                                text_content = (
                                    data.get('completion') or
                                    data.get('text') or 
                                    data.get('content') or
                                    data.get('message') or
                                    data.get('delta', {}).get('text') or
                                    data.get('choices', [{}])[0].get('delta', {}).get('content')
                                )
                                
                                if text_content:
                                    response_text += str(text_content)
                                    
                        except json.JSONDecodeError:
                            # If not JSON, treat as raw text (might be partial response)
                            if data_str not in ['', 'null', 'undefined']:
                                response_text += data_str
                            
            except UnicodeDecodeError:
                # Handle binary/compressed responses
                response_text = "Binary response received"
            
            # Final fallback: extract from JSON response
            if not response_text:
                try:
                    response_data = response.json()
                    response_text = (
                        response_data.get('completion') or
                        response_data.get('text') or
                        response_data.get('content') or
                        str(response_data) if response_data else ""
                    )
                except:
                    # Last resort: use status code to indicate success/failure
                    response_text = f"Claude response received (HTTP {response.status_code})"
            
            self.logger.debug(f"Received Claude response ({len(response_text)} chars)")
            return response_text.strip()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ClaudeAuthError("Rate limit exceeded - please wait before retrying")
            elif e.response.status_code == 401:
                raise ClaudeAuthError("Claude session expired - please refresh credentials")
            else:
                # Log response details for debugging
                self.logger.error(f"HTTP {e.response.status_code} response: {e.response.text[:500]}")
                raise ClaudeAuthError(f"Failed to send message: HTTP {e.response.status_code}")
        except Exception as e:
            raise ClaudeAuthError(f"Failed to send message: {e}")
    
    async def close(self):
        """Close the HTTP client and reset state."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._client_initialized = False
            self._auth_validated = False


def get_claude_client(session_key: Optional[str] = None):
    """
    Get the appropriate Claude client based on authentication strategy.
    
    Returns:
        ClaudeBrowserAuth instance
    """
    return ClaudeBrowserAuth(session_key=session_key)