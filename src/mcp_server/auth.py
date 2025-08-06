"""
Authentication and Authorization for MCP ADHD Server.

Implements session-based authentication with registration/login endpoints.
"""
import hashlib
import secrets
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

import structlog
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator

from mcp_server.config import settings
from mcp_server.models import User

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)


class RegistrationRequest(BaseModel):
    """User registration request."""
    name: str
    email: EmailStr
    password: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        if len(v.strip()) > 100:
            raise ValueError('Name must be less than 100 characters')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Almost there! Your password needs to be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Your password is a bit too long - let\'s keep it under 128 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Your password needs at least one letter (a-z or A-Z)')
        if not re.search(r'[0-9]', v):
            raise ValueError('Your password needs at least one number (0-9)')
        return v


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Almost there! Your new password needs to be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Your new password is a bit too long - let\'s keep it under 128 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Your new password needs at least one letter (a-z or A-Z)')
        if not re.search(r'[0-9]', v):
            raise ValueError('Your new password needs at least one number (0-9)')
        return v


class UserProfile(BaseModel):
    """User profile update request."""
    name: Optional[str] = None
    timezone: Optional[str] = None
    preferred_nudge_methods: Optional[list[str]] = None
    energy_patterns: Optional[dict] = None
    hyperfocus_indicators: Optional[list[str]] = None
    nudge_timing_preferences: Optional[dict] = None


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    message: str
    user: Optional[dict] = None
    session_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class UserData(BaseModel):
    """User data with password hash."""
    user_id: str
    email: str
    name: str
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    email_verified: bool = False
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None


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
        self._user_data: Dict[str, UserData] = {}  # Store password hashes
        self._email_to_user_id: Dict[str, str] = {}  # Email lookup
        
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
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            salt, hash_value = hashed.split(':', 1)
            password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
            return password_hash == hash_value
        except ValueError:
            return False
    
    def register_user(self, registration: RegistrationRequest) -> AuthResponse:
        """Register new user."""
        # Check if email already exists
        if registration.email in self._email_to_user_id:
            return AuthResponse(
                success=False,
                message="Good news! You already have an account with this email. Would you like to sign in instead?"
            )
        
        # Generate user ID
        user_id = secrets.token_urlsafe(16)
        
        # Hash password
        password_hash = self._hash_password(registration.password)
        
        # Create user data record
        user_data = UserData(
            user_id=user_id,
            email=registration.email,
            name=registration.name,
            password_hash=password_hash,
            created_at=datetime.utcnow()
        )
        
        # Create user model for app usage
        user = User(
            user_id=user_id,
            name=registration.name,
            email=registration.email,
            timezone="UTC",  # Default, user can change later
            preferred_nudge_methods=["web"],  # Default to web notifications
            energy_patterns={
                "peak_hours": [9, 10, 11, 14, 15, 16],
                "low_hours": [12, 13, 17, 18, 19]
            },
            hyperfocus_indicators=["long_sessions"],
            nudge_timing_preferences={
                "morning": "09:00",
                "afternoon": "14:00",
                "evening": "18:00"
            }
        )
        
        # Store user data
        self._user_data[user_id] = user_data
        self._users[user_id] = user
        self._email_to_user_id[registration.email] = user_id
        
        logger.info("User registered successfully", 
                   user_id=user_id, 
                   email=registration.email, 
                   name=registration.name)
        
        return AuthResponse(
            success=True,
            message=f"Welcome to MCP ADHD Server, {registration.name}! Your account has been created successfully.",
            user={
                "user_id": user_id,
                "name": registration.name,
                "email": registration.email,
                "created_at": user_data.created_at.isoformat()
            }
        )
    
    def login_user(self, login: LoginRequest, user_agent: str = None, ip_address: str = None) -> AuthResponse:
        """Login user and create session."""
        # Find user by email
        user_id = self._email_to_user_id.get(login.email)
        if not user_id:
            return AuthResponse(
                success=False,
                message="Hmm, that email and password don't match our records. Double-check your info, or would you like to reset your password?"
            )
        
        # Get user data
        user_data = self._user_data.get(user_id)
        if not user_data or not user_data.is_active:
            return AuthResponse(
                success=False,
                message="Account not found or inactive. Please contact support if you need assistance."
            )
        
        # Verify password
        if not self._verify_password(login.password, user_data.password_hash):
            logger.warning("Failed login attempt", email=login.email, ip=ip_address)
            return AuthResponse(
                success=False,
                message="Hmm, that email and password don't match our records. Double-check your info, or would you like to reset your password?"
            )
        
        # Create session
        session_id = self.create_session(user_id, user_agent, ip_address)
        session = self._sessions[session_id]
        
        # Update last login
        user_data.last_login = datetime.utcnow()
        
        # Get user model
        user = self._users[user_id]
        
        logger.info("User logged in successfully", user_id=user_id, email=login.email)
        
        return AuthResponse(
            success=True,
            message=f"Welcome back, {user.name}! You've been logged in successfully.",
            user={
                "user_id": user_id,
                "name": user.name,
                "email": user_data.email,
                "last_login": user_data.last_login.isoformat()
            },
            session_id=session_id,
            expires_at=session.expires_at
        )
    
    def logout_user(self, session_id: str) -> AuthResponse:
        """Logout user by revoking session."""
        if self.revoke_session(session_id):
            return AuthResponse(
                success=True,
                message="You've been logged out successfully. Thank you for using MCP ADHD Server!"
            )
        else:
            return AuthResponse(
                success=False,
                message="Session not found or already expired."
            )
    
    def update_user_profile(self, user_id: str, profile: UserProfile) -> AuthResponse:
        """Update user profile."""
        user = self._users.get(user_id)
        user_data = self._user_data.get(user_id)
        
        if not user or not user_data:
            return AuthResponse(
                success=False,
                message="User not found."
            )
        
        # Update user model
        if profile.name is not None:
            user.name = profile.name
            user_data.name = profile.name
        if profile.timezone is not None:
            user.timezone = profile.timezone
        if profile.preferred_nudge_methods is not None:
            user.preferred_nudge_methods = profile.preferred_nudge_methods
        if profile.energy_patterns is not None:
            user.energy_patterns = profile.energy_patterns
        if profile.hyperfocus_indicators is not None:
            user.hyperfocus_indicators = profile.hyperfocus_indicators
        if profile.nudge_timing_preferences is not None:
            user.nudge_timing_preferences = profile.nudge_timing_preferences
        
        logger.info("User profile updated", user_id=user_id)
        
        return AuthResponse(
            success=True,
            message="Your profile has been updated successfully!",
            user={
                "user_id": user_id,
                "name": user.name,
                "email": user_data.email,
                "timezone": user.timezone,
                "preferred_nudge_methods": user.preferred_nudge_methods
            }
        )
    
    def request_password_reset(self, email: str) -> AuthResponse:
        """Request password reset."""
        user_id = self._email_to_user_id.get(email)
        if not user_id:
            # Don't reveal if email exists or not for security
            return AuthResponse(
                success=True,
                message="If an account with this email exists, you will receive password reset instructions."
            )
        
        user_data = self._user_data.get(user_id)
        if not user_data or not user_data.is_active:
            return AuthResponse(
                success=True,
                message="If an account with this email exists, you will receive password reset instructions."
            )
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user_data.reset_token = reset_token
        user_data.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        logger.info("Password reset requested", email=email, user_id=user_id)
        
        # In a real implementation, you would send an email here
        # For now, we'll log the token for development
        logger.info("Password reset token generated", token=reset_token, user_id=user_id)
        
        return AuthResponse(
            success=True,
            message="If an account with this email exists, you will receive password reset instructions."
        )
    
    def reset_password(self, reset: PasswordResetConfirm) -> AuthResponse:
        """Reset password using token."""
        # Find user by reset token
        user_data = None
        user_id = None
        
        for uid, data in self._user_data.items():
            if data.reset_token == reset.token:
                user_data = data
                user_id = uid
                break
        
        if not user_data or not user_data.reset_token_expires:
            return AuthResponse(
                success=False,
                message="Invalid or expired reset token. Please request a new password reset."
            )
        
        # Check if token is expired
        if datetime.utcnow() > user_data.reset_token_expires:
            return AuthResponse(
                success=False,
                message="Reset token has expired. Please request a new password reset."
            )
        
        # Update password
        user_data.password_hash = self._hash_password(reset.new_password)
        user_data.reset_token = None
        user_data.reset_token_expires = None
        
        # Revoke all existing sessions for security
        sessions_to_revoke = [
            session_id for session_id, session in self._sessions.items()
            if session.user_id == user_id
        ]
        for session_id in sessions_to_revoke:
            self.revoke_session(session_id)
        
        logger.info("Password reset completed", user_id=user_id)
        
        return AuthResponse(
            success=True,
            message="Your password has been reset successfully. Please log in with your new password."
        )
    
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