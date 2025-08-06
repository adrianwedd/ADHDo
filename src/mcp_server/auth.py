"""
Authentication and Authorization for MCP ADHD Server.

Implements session-based authentication with optional API key support.
"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

import structlog
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from mcp_server.config import settings
from mcp_server.models import User

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)


class Session(BaseModel):
    """User session data."""
    session_id: str
    user_id: str
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if session is still valid."""
        return datetime.utcnow() < self.expires_at
    
    def refresh(self) -> None:
        """Refresh session expiry."""
        self.last_accessed = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=settings.session_duration_hours)


class APIKey(BaseModel):
    """API key data."""
    key_id: str
    key_hash: str
    user_id: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    permissions: list[str] = []


class AuthManager:
    """Manages authentication and authorization."""
    
    def __init__(self):
        # In-memory stores (TODO: replace with persistent storage)
        self._sessions: Dict[str, Session] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._users: Dict[str, User] = {}
        
        # Rate limiting
        self._request_counts: Dict[str, Dict[str, int]] = {}
        
        # Create default admin user if configured
        if settings.admin_username and settings.admin_password:
            self._create_admin_user()
    
    def _create_admin_user(self) -> None:
        """Create default admin user."""
        admin_user = User(
            user_id="admin",
            name=settings.admin_username,
            preferred_nudge_methods=["telegram"],
            telegram_chat_id=settings.telegram_chat_id
        )
        self._users["admin"] = admin_user
        
        logger.info("Created admin user", username=settings.admin_username)
    
    def generate_api_key(self, user_id: str, name: str) -> tuple[str, str]:
        """Generate new API key for user."""
        key_id = f"mk_{secrets.token_urlsafe(8)}"
        api_key = f"{key_id}.{secrets.token_urlsafe(32)}"
        
        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            created_at=datetime.utcnow(),
            permissions=["chat", "context", "tasks"]
        )
        
        self._api_keys[key_id] = api_key_obj
        
        logger.info("Generated API key", user_id=user_id, key_id=key_id, name=name)
        return key_id, api_key
    
    def create_session(
        self, 
        user_id: str, 
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Create new user session."""
        session_id = secrets.token_urlsafe(32)
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=settings.session_duration_hours),
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        self._sessions[session_id] = session
        
        logger.info("Created session", user_id=user_id, session_id=session_id[:8])
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate and refresh session."""
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        
        if not session.is_valid():
            # Clean up expired session
            del self._sessions[session_id]
            return None
        
        # Refresh session
        session.refresh()
        return session
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key."""
        if not api_key or '.' not in api_key:
            return None
        
        key_id = api_key.split('.')[0]
        
        if key_id not in self._api_keys:
            return None
        
        api_key_obj = self._api_keys[key_id]
        
        if not api_key_obj.is_active:
            return None
        
        # Verify key hash
        provided_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if provided_hash != api_key_obj.key_hash:
            return None
        
        # Update last used
        api_key_obj.last_used = datetime.utcnow()
        
        return api_key_obj
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    def create_user(self, user: User) -> None:
        """Create new user."""
        self._users[user.user_id] = user
        logger.info("Created user", user_id=user.user_id, name=user.name)
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke user session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Revoked session", session_id=session_id[:8])
            return True
        return False
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key."""
        if key_id in self._api_keys:
            self._api_keys[key_id].is_active = False
            logger.info("Revoked API key", key_id=key_id)
            return True
        return False
    
    def check_rate_limit(self, identifier: str, limit: int = 100, window: int = 3600) -> bool:
        """Check if request is within rate limits."""
        now = int(time.time())
        window_start = now - window
        
        if identifier not in self._request_counts:
            self._request_counts[identifier] = {}
        
        # Clean old entries
        requests = self._request_counts[identifier]
        for timestamp in list(requests.keys()):
            if timestamp < window_start:
                del requests[timestamp]
        
        # Count current requests in window
        current_count = sum(requests.values())
        
        if current_count >= limit:
            return False
        
        # Record this request
        requests[now] = requests.get(now, 0) + 1
        return True
    
    def cleanup_expired(self) -> None:
        """Clean up expired sessions and old rate limit data."""
        now = datetime.utcnow()
        
        # Clean expired sessions
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if not session.is_valid()
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
        if expired_sessions:
            logger.info("Cleaned up expired sessions", count=len(expired_sessions))
        
        # Clean old rate limit data (older than 1 hour)
        cutoff = int(time.time()) - 3600
        for identifier in list(self._request_counts.keys()):
            requests = self._request_counts[identifier]
            for timestamp in list(requests.keys()):
                if timestamp < cutoff:
                    del requests[timestamp]
            
            # Remove empty entries
            if not requests:
                del self._request_counts[identifier]


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Dependency to get current authenticated user."""
    
    user_id = None
    auth_method = "none"
    
    # Check session cookie first
    session_id = request.cookies.get("session_id")
    if session_id:
        session = auth_manager.validate_session(session_id)
        if session:
            user_id = session.user_id
            auth_method = "session"
    
    # Check API key if no valid session
    if not user_id and credentials:
        api_key = auth_manager.validate_api_key(credentials.credentials)
        if api_key:
            user_id = api_key.user_id
            auth_method = "api_key"
    
    # Check for development mode bypass
    if not user_id and settings.debug:
        # In debug mode, allow requests with X-User-ID header
        debug_user_id = request.headers.get("X-User-ID")
        if debug_user_id:
            user_id = debug_user_id
            auth_method = "debug"
            
            # Create debug user if doesn't exist
            if not auth_manager.get_user(user_id):
                debug_user = User(
                    user_id=user_id,
                    name=f"Debug User {user_id}",
                    preferred_nudge_methods=["telegram"]
                )
                auth_manager.create_user(debug_user)
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Use session cookie, API key, or X-User-ID header in debug mode."
        )
    
    # Rate limiting
    identifier = f"{auth_method}:{user_id}"
    if not auth_manager.check_rate_limit(identifier):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    user = auth_manager.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Log successful authentication
    logger.debug("User authenticated", user_id=user_id, method=auth_method)
    
    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Optional user dependency - returns None if not authenticated."""
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None