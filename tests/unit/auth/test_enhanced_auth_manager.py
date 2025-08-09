"""
Comprehensive tests for enhanced authentication system.

This module tests the production-grade security features including:
- Database-backed session persistence
- JWT secret rotation
- Account lockout mechanisms
- Security event logging
- Session hijacking protection
- ADHD-specific requirements
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_server.enhanced_auth import (
    EnhancedAuthManager, JWTManager, RegistrationRequest, LoginRequest,
    AuthResponse, SessionInfo
)
from mcp_server.db_models import (
    User as DBUser, Session as DBSession, JWTSecret, SecurityEvent,
    SessionActivity
)


class TestJWTManager:
    """Test JWT secret rotation and token management."""
    
    @pytest.fixture
    async def jwt_manager(self):
        """Create JWT manager for testing."""
        return JWTManager()
    
    @pytest.fixture
    async def mock_db(self):
        """Create mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db
    
    async def test_create_new_secret(self, jwt_manager, mock_db):
        """Test JWT secret creation and rotation."""
        # Mock database responses
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # Create new secret
        secret = await jwt_manager.create_new_secret(mock_db, "test_rotation")
        
        # Verify secret properties
        assert secret is not None
        assert len(secret) > 50  # Should be a long, secure secret
        
        # Verify database operations
        assert mock_db.execute.call_count >= 2  # Deactivate old + create new
        assert mock_db.commit.called
    
    async def test_get_active_secret(self, jwt_manager, mock_db):
        """Test retrieving active JWT secret."""
        # Mock active secret in database
        mock_secret = Mock()
        mock_secret.secret_key = jwt_manager._cipher.encrypt(b"test_secret").decode()
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_secret
        
        # Get active secret
        secret = await jwt_manager.get_active_secret(mock_db)
        
        # Verify decryption
        assert secret == "test_secret"
    
    async def test_generate_and_verify_token(self, jwt_manager, mock_db):
        """Test JWT token generation and verification."""
        # Mock active secret
        test_secret = "test_secret_123"
        with patch.object(jwt_manager, 'get_active_secret', return_value=test_secret):
            # Generate token
            payload = {"user_id": "test_user", "email": "test@example.com"}
            token = await jwt_manager.generate_token(mock_db, payload)
            
            assert token is not None
            assert isinstance(token, str)
            
            # Verify token
            decoded = await jwt_manager.verify_token(mock_db, token)
            assert decoded is not None
            assert decoded["user_id"] == "test_user"
            assert decoded["email"] == "test@example.com"
            assert "exp" in decoded
            assert "iat" in decoded


class TestEnhancedAuthManager:
    """Test enhanced authentication manager with database persistence."""
    
    @pytest.fixture
    async def auth_manager(self):
        """Create enhanced auth manager for testing."""
        return EnhancedAuthManager()
    
    @pytest.fixture
    async def mock_db(self):
        """Create mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.add = Mock()
        return db
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {
            "user-agent": "test-agent",
            "accept-language": "en-US",
            "accept-encoding": "gzip"
        }
        return request
    
    @pytest.fixture
    def valid_registration(self):
        """Create valid registration request."""
        return RegistrationRequest(
            name="Test User",
            email="test@example.com",
            password="TestPass123"
        )
    
    @pytest.fixture
    def valid_login(self):
        """Create valid login request."""
        return LoginRequest(
            email="test@example.com",
            password="TestPass123"
        )
    
    async def test_register_user_success(self, auth_manager, mock_db, valid_registration):
        """Test successful user registration."""
        # Mock no existing user
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # Register user
        result = await auth_manager.register_user(mock_db, valid_registration)
        
        # Verify success
        assert result.success is True
        assert "Welcome to MCP ADHD Server" in result.message
        assert result.user is not None
        assert result.user["email"] == valid_registration.email
        assert result.user["name"] == valid_registration.name
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
    
    async def test_register_user_duplicate_email(self, auth_manager, mock_db, valid_registration):
        """Test registration with duplicate email."""
        # Mock existing user
        existing_user = Mock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
        
        # Attempt registration
        result = await auth_manager.register_user(mock_db, valid_registration)
        
        # Verify failure
        assert result.success is False
        assert "already have an account" in result.message
        assert not mock_db.add.called
    
    async def test_login_user_success(self, auth_manager, mock_db, valid_login, mock_request):
        """Test successful user login."""
        # Mock existing user with valid password
        mock_user = Mock(spec=DBUser)
        mock_user.user_id = "test_user_id"
        mock_user.email = valid_login.email
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.password_hash = await auth_manager._hash_password(valid_login.password)
        mock_user.failed_login_attempts = 0
        mock_user.account_locked_until = None
        mock_user.mfa_enabled = False
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        # Mock session creation
        with patch.object(auth_manager, 'create_session') as mock_create_session:
            mock_session = SessionInfo(
                session_id="test_session",
                user_id="test_user_id",
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
                csrf_token="test_csrf"
            )
            mock_create_session.return_value = mock_session
            
            # Login user
            result = await auth_manager.login_user(mock_db, valid_login, mock_request)
            
            # Verify success
            assert result.success is True
            assert "Welcome back" in result.message
            assert result.session_id == "test_session"
            assert result.csrf_token == "test_csrf"
            assert result.user is not None
    
    async def test_login_user_invalid_password(self, auth_manager, mock_db, valid_login, mock_request):
        """Test login with invalid password."""
        # Mock existing user with different password
        mock_user = Mock(spec=DBUser)
        mock_user.user_id = "test_user_id"
        mock_user.email = valid_login.email
        mock_user.is_active = True
        mock_user.password_hash = await auth_manager._hash_password("different_password")
        mock_user.failed_login_attempts = 0
        mock_user.account_locked_until = None
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        # Attempt login
        result = await auth_manager.login_user(mock_db, valid_login, mock_request)
        
        # Verify failure
        assert result.success is False
        assert "don't match our records" in result.message
        assert mock_user.failed_login_attempts == 1
    
    async def test_account_lockout_mechanism(self, auth_manager, mock_db, valid_login, mock_request):
        """Test account lockout after failed attempts."""
        # Mock user with multiple failed attempts
        mock_user = Mock(spec=DBUser)
        mock_user.user_id = "test_user_id"
        mock_user.email = valid_login.email
        mock_user.is_active = True
        mock_user.password_hash = await auth_manager._hash_password("different_password")
        mock_user.failed_login_attempts = 4  # One more will trigger lockout
        mock_user.account_locked_until = None
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
        
        # Attempt login (this should trigger lockout)
        result = await auth_manager.login_user(mock_db, valid_login, mock_request)
        
        # Verify lockout triggered
        assert result.success is False
        assert mock_user.failed_login_attempts == 5
        assert mock_user.account_locked_until is not None
        assert mock_user.account_locked_until > datetime.utcnow()
    
    async def test_create_session_with_security(self, auth_manager, mock_db, mock_request):
        """Test secure session creation."""
        user_id = "test_user_id"
        
        # Create session
        session_info = await auth_manager.create_session(
            mock_db, user_id, mock_request, remember_me=True
        )
        
        # Verify session properties
        assert session_info.session_id is not None
        assert len(session_info.session_id) > 50  # Should be long and secure
        assert session_info.user_id == user_id
        assert session_info.device_fingerprint is not None
        assert session_info.expires_at > datetime.utcnow()
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called
    
    async def test_validate_session_with_security_checks(self, auth_manager, mock_db, mock_request):
        """Test session validation with security checks."""
        session_id = "test_session_id"
        
        # Mock valid session in database
        mock_session = Mock(spec=DBSession)
        mock_session.session_id = session_id
        mock_session.user_id = "test_user_id"
        mock_session.is_active = True
        mock_session.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_session.revoked_at = None
        mock_session.ip_address = "127.0.0.1"  # Same as request
        mock_session.device_fingerprint = await auth_manager._generate_device_fingerprint(mock_request)
        mock_session.created_at = datetime.utcnow()
        mock_session.last_accessed = datetime.utcnow()
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        
        # Validate session
        session_info = await auth_manager.validate_session(mock_db, session_id, mock_request)
        
        # Verify validation success
        assert session_info is not None
        assert session_info.session_id == session_id
        assert session_info.user_id == "test_user_id"
        
        # Verify session was refreshed
        assert mock_db.commit.called
    
    async def test_session_hijacking_protection(self, auth_manager, mock_db, mock_request):
        """Test session hijacking protection."""
        session_id = "test_session_id"
        
        # Mock session with different IP address
        mock_session = Mock(spec=DBSession)
        mock_session.session_id = session_id
        mock_session.user_id = "test_user_id"
        mock_session.is_active = True
        mock_session.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_session.revoked_at = None
        mock_session.ip_address = "192.168.1.100"  # Different from request
        mock_session.device_fingerprint = "different_fingerprint"
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_session
        
        # Attempt to validate session (should be revoked due to IP change)
        session_info = await auth_manager.validate_session(mock_db, session_id, mock_request)
        
        # Verify session was revoked for security
        assert session_info is None
        assert mock_session.is_active is False
        assert mock_session.revoked_at is not None
        assert mock_session.revocation_reason == "security_violation"
    
    async def test_cleanup_expired_sessions(self, auth_manager, mock_db):
        """Test cleanup of expired sessions."""
        # Mock database update result
        mock_result = Mock()
        mock_result.rowcount = 5  # 5 sessions cleaned up
        mock_db.execute.return_value = mock_result
        
        # Clean up sessions
        cleaned_count = await auth_manager.cleanup_expired_sessions(mock_db)
        
        # Verify cleanup
        assert cleaned_count == 5
        assert mock_db.execute.called
        assert mock_db.commit.called


class TestPasswordSecurity:
    """Test password hashing and validation security."""
    
    @pytest.fixture
    async def auth_manager(self):
        return EnhancedAuthManager()
    
    async def test_password_hashing_security(self, auth_manager):
        """Test bcrypt password hashing with proper salt."""
        password = "TestPassword123"
        
        # Hash password
        hash1 = await auth_manager._hash_password(password)
        hash2 = await auth_manager._hash_password(password)
        
        # Verify hashes are different (due to salt)
        assert hash1 != hash2
        assert len(hash1) > 50  # bcrypt hashes are long
        assert hash1.startswith("$2b$")  # bcrypt identifier
        
        # Verify both hashes validate the same password
        assert await auth_manager._verify_password(password, hash1)
        assert await auth_manager._verify_password(password, hash2)
        
        # Verify wrong password fails
        assert not await auth_manager._verify_password("wrong", hash1)
    
    async def test_password_validation_timing_attack_protection(self, auth_manager):
        """Test that password validation takes consistent time."""
        import time
        
        password = "TestPassword123"
        hash_value = await auth_manager._hash_password(password)
        
        # Time correct password validation
        start_time = time.time()
        result1 = await auth_manager._verify_password(password, hash_value)
        correct_time = time.time() - start_time
        
        # Time incorrect password validation
        start_time = time.time()
        result2 = await auth_manager._verify_password("wrong_password", hash_value)
        incorrect_time = time.time() - start_time
        
        # Verify results
        assert result1 is True
        assert result2 is False
        
        # Times should be similar (within reasonable variance for timing attack protection)
        time_diff = abs(correct_time - incorrect_time)
        assert time_diff < 0.01  # Within 10ms (bcrypt naturally protects against this)


class TestSecurityEventLogging:
    """Test security event logging and monitoring."""
    
    @pytest.fixture
    async def auth_manager(self):
        return EnhancedAuthManager()
    
    @pytest.fixture
    async def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db
    
    async def test_security_event_logging(self, auth_manager, mock_db):
        """Test security event logging."""
        await auth_manager._log_security_event(
            mock_db,
            event_type="failed_login",
            severity="medium",
            description="Test security event",
            user_id="test_user",
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            metadata={"test": "data"}
        )
        
        # Verify event was logged
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Verify SecurityEvent was created with correct properties
        added_event = mock_db.add.call_args[0][0]
        assert added_event.event_type == "failed_login"
        assert added_event.severity == "medium"
        assert added_event.user_id == "test_user"
        assert added_event.ip_address == "127.0.0.1"
    
    async def test_session_activity_logging(self, auth_manager, mock_db):
        """Test session activity logging."""
        await auth_manager._log_session_activity(
            mock_db,
            session_id="test_session",
            user_id="test_user",
            activity_type="login",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            endpoint="/api/auth/login",
            request_method="POST",
            response_status=200,
            risk_score=0.5
        )
        
        # Verify activity was logged
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Verify SessionActivity was created
        added_activity = mock_db.add.call_args[0][0]
        assert added_activity.activity_type == "login"
        assert added_activity.risk_score == 0.5
        assert added_activity.response_status == 200


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for the complete authentication flow."""
    
    async def test_complete_registration_and_login_flow(self):
        """Test complete user registration and login flow."""
        # This would be a more comprehensive test with a real database
        # For now, we'll use mocks but structure it as an integration test
        pass
    
    async def test_session_persistence_across_restarts(self):
        """Test that sessions persist across server restarts."""
        # This test would verify database persistence
        pass
    
    async def test_adhd_performance_requirements(self):
        """Test that authentication meets ADHD performance requirements (<3s)."""
        # This test would measure actual response times
        pass


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])