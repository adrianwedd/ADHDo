"""
Unit tests for authentication manager.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch

from mcp_server.auth import AuthManager
from tests.utils import TestDataFactory


@pytest.mark.unit
@pytest.mark.auth
class TestAuthManager:
    """Test AuthManager functionality."""
    
    def test_auth_manager_initialization(self, auth_manager):
        """Test auth manager initialization."""
        assert auth_manager is not None
        assert hasattr(auth_manager, 'secret_key')
        assert hasattr(auth_manager, 'algorithm')
        assert hasattr(auth_manager, 'access_token_expire_minutes')
        assert auth_manager.algorithm == "HS256"
    
    def test_password_hashing(self, auth_manager):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        # Hash password
        hashed = auth_manager.hash_password(password)
        
        assert hashed != password  # Should be hashed
        assert len(hashed) > 50  # Should be substantial length
        assert hashed.startswith("$2b$")  # bcrypt format
        
        # Verify correct password
        assert auth_manager.verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert auth_manager.verify_password("wrong_password", hashed) is False
    
    def test_jwt_token_creation(self, auth_manager, test_user):
        """Test JWT token creation."""
        token_data = {
            "user_id": test_user.user_id,
            "email": test_user.email,
            "name": test_user.name
        }
        
        token = auth_manager.create_access_token(token_data)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT format: header.payload.signature
        
        # Verify token can be decoded
        decoded = jwt.decode(
            token, 
            auth_manager.secret_key, 
            algorithms=[auth_manager.algorithm]
        )
        
        assert decoded["user_id"] == test_user.user_id
        assert decoded["email"] == test_user.email
        assert "exp" in decoded  # Expiration time
        assert "iat" in decoded  # Issued at time
    
    def test_jwt_token_verification(self, auth_manager, test_user):
        """Test JWT token verification."""
        # Create valid token
        token_data = {"user_id": test_user.user_id, "email": test_user.email}
        valid_token = auth_manager.create_access_token(token_data)
        
        # Verify valid token
        decoded_data = auth_manager.verify_access_token(valid_token)
        assert decoded_data is not None
        assert decoded_data["user_id"] == test_user.user_id
        assert decoded_data["email"] == test_user.email
        
        # Test invalid token
        invalid_token = "invalid.jwt.token"
        decoded_invalid = auth_manager.verify_access_token(invalid_token)
        assert decoded_invalid is None
        
        # Test tampered token
        tampered_token = valid_token[:-10] + "tamperedXX"
        decoded_tampered = auth_manager.verify_access_token(tampered_token)
        assert decoded_tampered is None
    
    def test_token_expiration(self, auth_manager, test_user):
        """Test JWT token expiration."""
        # Create token with short expiration
        with patch.object(auth_manager, 'access_token_expire_minutes', 0.01):  # ~0.6 seconds
            token_data = {"user_id": test_user.user_id}
            short_token = auth_manager.create_access_token(token_data)
            
            # Should be valid immediately
            decoded = auth_manager.verify_access_token(short_token)
            assert decoded is not None
        
        # Note: In real test, would need to wait for expiration or mock time
        # For now, create expired token manually
        expired_payload = {
            "user_id": test_user.user_id,
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        expired_token = jwt.encode(
            expired_payload, 
            auth_manager.secret_key, 
            algorithm=auth_manager.algorithm
        )
        
        # Should be invalid due to expiration
        decoded_expired = auth_manager.verify_access_token(expired_token)
        assert decoded_expired is None
    
    async def test_user_authentication(self, auth_manager, db_service):
        """Test user authentication workflow."""
        # Create user with password
        password = "secure_password_123"
        hashed_password = auth_manager.hash_password(password)
        
        user = await db_service.create_user(
            name="Auth Test User",
            email="auth@example.com",
            password_hash=hashed_password
        )
        
        # Test successful authentication
        authenticated_user = await auth_manager.authenticate_user(
            db_service, "auth@example.com", password
        )
        
        assert authenticated_user is not None
        assert authenticated_user.user_id == user.user_id
        assert authenticated_user.email == "auth@example.com"
        
        # Test failed authentication - wrong password
        failed_auth = await auth_manager.authenticate_user(
            db_service, "auth@example.com", "wrong_password"
        )
        assert failed_auth is None
        
        # Test failed authentication - wrong email
        failed_auth_email = await auth_manager.authenticate_user(
            db_service, "wrong@example.com", password
        )
        assert failed_auth_email is None
    
    async def test_api_key_validation(self, auth_manager, db_service, test_user):
        """Test API key validation."""
        # Create API key
        key_id, api_key = await db_service.create_api_key(
            user_id=test_user.user_id,
            name="Test API Key",
            permissions=["chat", "tasks"]
        )
        
        # Validate API key
        validated_user = await auth_manager.validate_api_key(db_service, api_key)
        
        assert validated_user is not None
        assert validated_user.user_id == test_user.user_id
        
        # Test invalid API key
        invalid_user = await auth_manager.validate_api_key(
            db_service, "invalid_api_key"
        )
        assert invalid_user is None
        
        # Test revoked API key
        await db_service.api_keys.revoke(key_id)
        revoked_user = await auth_manager.validate_api_key(db_service, api_key)
        assert revoked_user is None
    
    async def test_session_validation(self, auth_manager, db_service, test_user):
        """Test session validation."""
        # Create session
        session_id = await db_service.create_session(
            user_id=test_user.user_id,
            duration_hours=24,
            user_agent="Test/1.0",
            ip_address="127.0.0.1"
        )
        
        # Validate session
        session_user = await auth_manager.validate_session(db_service, session_id)
        
        assert session_user is not None
        assert session_user.user_id == test_user.user_id
        
        # Test invalid session
        invalid_user = await auth_manager.validate_session(
            db_service, "invalid_session_id"
        )
        assert invalid_user is None
        
        # Test expired session (would need time manipulation in real test)
    
    def test_permission_checking(self, auth_manager):
        """Test permission checking functionality."""
        # Test basic permissions
        user_permissions = ["chat", "tasks", "health"]
        
        assert auth_manager.has_permission(user_permissions, "chat") is True
        assert auth_manager.has_permission(user_permissions, "tasks") is True
        assert auth_manager.has_permission(user_permissions, "admin") is False
        
        # Test wildcard permissions
        admin_permissions = ["*"]
        assert auth_manager.has_permission(admin_permissions, "chat") is True
        assert auth_manager.has_permission(admin_permissions, "admin") is True
        assert auth_manager.has_permission(admin_permissions, "any_permission") is True
        
        # Test hierarchical permissions
        hierarchical_permissions = ["tasks:read", "tasks:write", "health:read"]
        assert auth_manager.has_permission(hierarchical_permissions, "tasks:read") is True
        assert auth_manager.has_permission(hierarchical_permissions, "tasks:write") is True
        assert auth_manager.has_permission(hierarchical_permissions, "tasks:delete") is False
        assert auth_manager.has_permission(hierarchical_permissions, "health:read") is True
        assert auth_manager.has_permission(hierarchical_permissions, "health:write") is False
    
    def test_rate_limiting(self, auth_manager):
        """Test authentication rate limiting."""
        client_ip = "192.168.1.100"
        
        # Test multiple failed attempts
        for i in range(3):  # Below limit
            allowed = auth_manager.check_rate_limit(client_ip, "login_attempt")
            assert allowed is True
        
        # Should still be allowed (below limit)
        allowed = auth_manager.check_rate_limit(client_ip, "login_attempt")
        assert allowed is True
        
        # Exceed limit
        for i in range(10):  # Exceed typical limit
            auth_manager.record_failed_attempt(client_ip)
        
        # Should now be rate limited
        blocked = auth_manager.is_rate_limited(client_ip)
        assert blocked is True
    
    def test_security_headers(self, auth_manager):
        """Test security headers generation."""
        headers = auth_manager.get_security_headers()
        
        expected_headers = {
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        }
        
        for header in expected_headers:
            assert header in headers
        
        # Verify specific values
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert "max-age" in headers["Strict-Transport-Security"]
    
    async def test_login_workflow(self, auth_manager, db_service):
        """Test complete login workflow."""
        # Create user
        password = "login_test_password"
        hashed_password = auth_manager.hash_password(password)
        
        user = await db_service.create_user(
            name="Login Test User",
            email="login@example.com",
            password_hash=hashed_password
        )
        
        # Attempt login
        login_result = await auth_manager.login(
            db_service,
            email="login@example.com",
            password=password,
            user_agent="TestClient/1.0",
            ip_address="127.0.0.1"
        )
        
        assert login_result is not None
        assert "access_token" in login_result
        assert "user" in login_result
        assert "session_id" in login_result
        
        # Verify token
        token = login_result["access_token"]
        decoded = auth_manager.verify_access_token(token)
        assert decoded["user_id"] == user.user_id
        
        # Verify session was created
        session_id = login_result["session_id"]
        session_user = await db_service.validate_session(session_id)
        assert session_user.user_id == user.user_id
    
    async def test_logout_workflow(self, auth_manager, db_service, test_user_session):
        """Test logout workflow."""
        # Logout should invalidate session
        await auth_manager.logout(db_service, test_user_session)
        
        # Session should no longer be valid
        session_user = await db_service.validate_session(test_user_session)
        assert session_user is None
    
    def test_token_refresh(self, auth_manager, test_user):
        """Test token refresh functionality."""
        # Create initial token
        original_token_data = {"user_id": test_user.user_id, "email": test_user.email}
        original_token = auth_manager.create_access_token(original_token_data)
        
        # Refresh token (create new one with same data)
        refreshed_token = auth_manager.refresh_access_token(original_token)
        
        assert refreshed_token is not None
        assert refreshed_token != original_token  # Should be different
        
        # Both tokens should be valid (until original expires)
        original_decoded = auth_manager.verify_access_token(original_token)
        refreshed_decoded = auth_manager.verify_access_token(refreshed_token)
        
        assert original_decoded is not None
        assert refreshed_decoded is not None
        assert original_decoded["user_id"] == refreshed_decoded["user_id"]
    
    async def test_multi_factor_authentication(self, auth_manager, db_service, test_user):
        """Test multi-factor authentication (MFA) if implemented."""
        # Enable MFA for user
        await auth_manager.enable_mfa(db_service, test_user.user_id)
        
        # Check MFA status
        mfa_enabled = await auth_manager.is_mfa_enabled(db_service, test_user.user_id)
        assert mfa_enabled is True
        
        # Generate MFA secret
        secret = await auth_manager.generate_mfa_secret(test_user.user_id)
        assert secret is not None
        assert len(secret) >= 16  # Should be substantial length
        
        # Generate TOTP code (would need time-based testing)
        # totp_code = auth_manager.generate_totp_code(secret)
        # assert len(totp_code) == 6  # Standard TOTP length
        
        # Verify TOTP code (would need actual TOTP implementation)
        # is_valid = auth_manager.verify_totp_code(secret, totp_code)
        # assert is_valid is True
    
    def test_password_strength_validation(self, auth_manager):
        """Test password strength validation."""
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "qwerty",
            ""
        ]
        
        for weak_password in weak_passwords:
            is_strong = auth_manager.is_password_strong(weak_password)
            assert is_strong is False
        
        # Test strong passwords
        strong_passwords = [
            "MyStr0ngP@ssw0rd!",
            "C0mpl3x_P@ssw0rd_2024",
            "SecureP@ss123Word!"
        ]
        
        for strong_password in strong_passwords:
            is_strong = auth_manager.is_password_strong(strong_password)
            assert is_strong is True
    
    async def test_account_lockout(self, auth_manager, db_service):
        """Test account lockout after failed attempts."""
        # Create user
        password = "lockout_test_password"
        hashed_password = auth_manager.hash_password(password)
        
        user = await db_service.create_user(
            name="Lockout Test User",
            email="lockout@example.com",
            password_hash=hashed_password
        )
        
        # Attempt multiple failed logins
        for i in range(5):  # Assume 5 is the lockout threshold
            result = await auth_manager.authenticate_user(
                db_service, "lockout@example.com", "wrong_password"
            )
            assert result is None
        
        # Account should now be locked
        is_locked = await auth_manager.is_account_locked(db_service, user.user_id)
        assert is_locked is True
        
        # Even correct password should fail when locked
        result = await auth_manager.authenticate_user(
            db_service, "lockout@example.com", password
        )
        assert result is None  # Should be None due to lockout
    
    async def test_security_audit_logging(self, auth_manager, db_service):
        """Test security audit logging."""
        # Perform various auth operations that should be logged
        events_to_test = [
            ("user_login", "successful"),
            ("user_login", "failed"),
            ("api_key_used", "successful"),
            ("session_created", "successful"),
            ("password_changed", "successful")
        ]
        
        for event_type, status in events_to_test:
            await auth_manager.log_security_event(
                event_type=event_type,
                status=status,
                user_id="test_user_id",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
                details={"test": True}
            )
        
        # Retrieve audit logs
        audit_logs = await auth_manager.get_audit_logs(
            limit=10,
            event_types=["user_login", "api_key_used"]
        )
        
        assert len(audit_logs) >= 3  # Should have logged events
        
        for log in audit_logs:
            assert "timestamp" in log
            assert "event_type" in log
            assert "status" in log
            assert "ip_address" in log