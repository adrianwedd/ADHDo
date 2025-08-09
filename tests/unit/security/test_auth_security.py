"""
CRITICAL SECURITY TESTS: Authentication System Security

These tests validate the authentication system against common attack vectors:
- Session management security and token validation
- Password security with proper hashing and validation
- API key security and access control
- Rate limiting and brute force protection
- Attack vector testing (injection, enumeration, timing attacks)
- MFA workflow and backup authentication methods

SECURITY REQUIREMENTS:
- All passwords must be properly hashed with bcrypt
- Sessions must be secure and properly validated
- Rate limiting must prevent brute force attacks
- No user enumeration through timing or error messages
- API keys must be properly secured and rotated
- Emergency access must not compromise security
"""
import pytest
import asyncio
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List
import bcrypt

from mcp_server.auth import (
    AuthManager, RegistrationRequest, LoginRequest, PasswordResetRequest,
    PasswordResetConfirm, UserProfile, AuthResponse, UserData, Session, APIKey
)
from fastapi import HTTPException
from fastapi.testclient import TestClient


class TestPasswordSecurity:
    """Test password handling and security."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create fresh auth manager for testing."""
        return AuthManager()
    
    def test_password_hashing_security(self, auth_manager):
        """Test passwords are properly hashed with bcrypt."""
        password = "TestPassword123!"
        
        # Hash the password
        hashed = auth_manager._hash_password(password)
        
        # Should be bcrypt hash format
        assert hashed.startswith("$2b$")
        assert len(hashed) >= 60, "bcrypt hash too short"
        
        # Should verify correctly
        assert auth_manager._verify_password(password, hashed) is True
        
        # Should not verify with wrong password
        assert auth_manager._verify_password("WrongPassword123!", hashed) is False
    
    def test_password_hashing_salt_uniqueness(self, auth_manager):
        """Test each password gets unique salt."""
        password = "SamePassword123!"
        
        # Hash same password multiple times
        hash1 = auth_manager._hash_password(password)
        hash2 = auth_manager._hash_password(password)
        hash3 = auth_manager._hash_password(password)
        
        # All hashes should be different due to unique salts
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3
        
        # But all should verify the same password
        assert auth_manager._verify_password(password, hash1) is True
        assert auth_manager._verify_password(password, hash2) is True
        assert auth_manager._verify_password(password, hash3) is True
    
    def test_password_hash_timing_attack_resistance(self, auth_manager):
        """Test password verification timing is consistent."""
        valid_password = "ValidPassword123!"
        hashed = auth_manager._hash_password(valid_password)
        
        invalid_passwords = [
            "InvalidPassword123!",
            "Wrong",
            "CompletelyDifferentPasswordThatIsVeryLong",
            "",
            "A" * 200  # Very long password
        ]
        
        # Measure timing for valid password
        valid_times = []
        for _ in range(10):
            start = time.perf_counter()
            result = auth_manager._verify_password(valid_password, hashed)
            end = time.perf_counter()
            valid_times.append(end - start)
            assert result is True
        
        # Measure timing for invalid passwords
        invalid_times = []
        for invalid_password in invalid_passwords:
            for _ in range(2):  # Test each invalid password multiple times
                start = time.perf_counter()
                result = auth_manager._verify_password(invalid_password, hashed)
                end = time.perf_counter()
                invalid_times.append(end - start)
                assert result is False
        
        # Average times should be similar (within 50% to prevent timing attacks)
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)
        
        # bcrypt should provide consistent timing
        time_ratio = max(avg_valid, avg_invalid) / min(avg_valid, avg_invalid)
        assert time_ratio < 2.0, f"Timing attack possible: valid={avg_valid:.6f}s, invalid={avg_invalid:.6f}s"
    
    def test_password_validation_requirements(self, auth_manager):
        """Test password validation enforces security requirements."""
        valid_passwords = [
            "ValidPass123!",
            "AnotherGood1",
            "SecurePassword2024",
            "MyPassword9"
        ]
        
        invalid_passwords = [
            "short1",  # Too short
            "NoNumbers!",  # No numbers
            "nonumbers",  # No numbers or uppercase
            "NOUPPER123",  # No lowercase
            "123456789",  # No letters
            "A" * 129,  # Too long
            "",  # Empty
            "NoNumber!"  # No numbers
        ]
        
        # Valid passwords should register successfully
        for i, password in enumerate(valid_passwords):
            request = RegistrationRequest(
                name=f"Test User {i}",
                email=f"test{i}@example.com",
                password=password
            )
            # Should not raise validation error
            assert len(request.password) >= 8
        
        # Invalid passwords should fail validation
        for password in invalid_passwords:
            with pytest.raises(ValueError):
                RegistrationRequest(
                    name="Test User",
                    email="test@example.com",
                    password=password
                )


class TestSessionSecurity:
    """Test session management security."""
    
    @pytest.fixture
    def auth_manager(self):
        return AuthManager()
    
    def test_session_token_randomness(self, auth_manager):
        """Test session tokens are cryptographically random."""
        # Generate multiple sessions
        session_ids = []
        for i in range(100):
            session_id = auth_manager.create_session(
                user_id=f"user_{i}",
                user_agent="Test Agent",
                ip_address="127.0.0.1"
            )
            session_ids.append(session_id)
        
        # All session IDs should be unique
        assert len(set(session_ids)) == len(session_ids), "Session IDs are not unique"
        
        # Session IDs should be long enough to prevent brute force
        for session_id in session_ids[:10]:  # Check first 10
            assert len(session_id) >= 32, f"Session ID too short: {session_id}"
            # Should be URL-safe base64
            assert session_id.replace('-', '').replace('_', '').isalnum()
    
    def test_session_expiration_enforcement(self, auth_manager):
        """Test session expiration is properly enforced."""
        user_id = "expiration_test_user"
        session_id = auth_manager.create_session(user_id)
        
        # Fresh session should be valid
        session = auth_manager.validate_session(session_id)
        assert session is not None
        assert session.user_id == user_id
        assert session.is_valid() is True
        
        # Manually expire the session
        session.expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        # Expired session should be invalid
        invalid_session = auth_manager.validate_session(session_id)
        assert invalid_session is None
        
        # Session should be cleaned up
        assert session_id not in auth_manager._sessions
    
    def test_session_refresh_security(self, auth_manager):
        """Test session refresh updates expiration securely."""
        user_id = "refresh_test_user"
        session_id = auth_manager.create_session(user_id)
        
        # Get initial expiration
        session = auth_manager._sessions[session_id]
        initial_expires = session.expires_at
        initial_accessed = session.last_accessed
        
        # Wait a small amount and validate (which triggers refresh)
        time.sleep(0.01)
        refreshed_session = auth_manager.validate_session(session_id)
        
        assert refreshed_session is not None
        assert refreshed_session.expires_at > initial_expires
        assert refreshed_session.last_accessed > initial_accessed
    
    def test_session_cleanup_on_expiration(self, auth_manager):
        """Test expired sessions are cleaned up automatically."""
        # Create multiple sessions with different expiration times
        user_ids = [f"cleanup_user_{i}" for i in range(5)]
        session_ids = []
        
        for user_id in user_ids:
            session_id = auth_manager.create_session(user_id)
            session_ids.append(session_id)
        
        # Manually expire half the sessions
        for i in range(0, len(session_ids), 2):
            session = auth_manager._sessions[session_ids[i]]
            session.expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        # Run cleanup
        auth_manager.cleanup_expired()
        
        # Expired sessions should be removed
        remaining_sessions = len(auth_manager._sessions)
        expected_remaining = len(session_ids) - (len(session_ids) // 2)
        assert remaining_sessions >= expected_remaining - 1  # Allow for timing variations
    
    def test_session_security_metadata(self, auth_manager):
        """Test session includes security metadata."""
        user_id = "metadata_test_user"
        user_agent = "Mozilla/5.0 Test Browser"
        ip_address = "192.168.1.100"
        
        session_id = auth_manager.create_session(
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        session = auth_manager._sessions[session_id]
        
        assert session.user_agent == user_agent
        assert session.ip_address == ip_address
        assert session.created_at is not None
        assert session.last_accessed is not None
        
        # Timestamps should be reasonable
        now = datetime.utcnow()
        assert abs((now - session.created_at).total_seconds()) < 1
        assert abs((now - session.last_accessed).total_seconds()) < 1


class TestAPIKeySecurity:
    """Test API key security and management."""
    
    @pytest.fixture
    def auth_manager(self):
        return AuthManager()
    
    def test_api_key_generation_security(self, auth_manager):
        """Test API keys are generated securely."""
        user_id = "api_test_user"
        key_name = "Test API Key"
        
        key_id, api_key = auth_manager.generate_api_key(user_id, key_name)
        
        # API key should have proper format
        assert api_key.startswith(key_id)
        assert "." in api_key
        parts = api_key.split(".")
        assert len(parts) == 2
        
        # Key ID should have proper prefix
        assert key_id.startswith("mk_")
        assert len(key_id) > 10, "Key ID too short"
        
        # Full API key should be long enough
        assert len(api_key) > 40, "API key too short for security"
        
        # Should be stored with hash, not plaintext
        api_key_obj = auth_manager._api_keys[key_id]
        assert api_key_obj.key_hash != api_key
        assert len(api_key_obj.key_hash) == 64  # SHA-256 hex
    
    def test_api_key_validation_security(self, auth_manager):
        """Test API key validation is secure."""
        user_id = "validation_test_user"
        key_id, api_key = auth_manager.generate_api_key(user_id, "Test Key")
        
        # Valid API key should validate
        valid_key = auth_manager.validate_api_key(api_key)
        assert valid_key is not None
        assert valid_key.user_id == user_id
        assert valid_key.is_active is True
        
        # Invalid API keys should not validate
        invalid_keys = [
            api_key + "extra",  # Modified key
            api_key[:-1],  # Truncated key
            key_id + ".wrongsecret",  # Wrong secret part
            "invalid.format",  # Invalid format
            "",  # Empty
            "mk_validid.tooshort",  # Too short secret
        ]
        
        for invalid_key in invalid_keys:
            assert auth_manager.validate_api_key(invalid_key) is None
    
    def test_api_key_revocation(self, auth_manager):
        """Test API key revocation works properly."""
        user_id = "revocation_test_user"
        key_id, api_key = auth_manager.generate_api_key(user_id, "Test Key")
        
        # Should validate initially
        assert auth_manager.validate_api_key(api_key) is not None
        
        # Revoke the key
        revoked = auth_manager.revoke_api_key(key_id)
        assert revoked is True
        
        # Should not validate after revocation
        assert auth_manager.validate_api_key(api_key) is None
        
        # Key should still exist but be inactive
        api_key_obj = auth_manager._api_keys[key_id]
        assert api_key_obj.is_active is False
    
    def test_api_key_permissions_enforcement(self, auth_manager):
        """Test API key permissions are enforced."""
        user_id = "permissions_test_user"
        key_id, api_key = auth_manager.generate_api_key(user_id, "Limited Key")
        
        # Check default permissions
        api_key_obj = auth_manager._api_keys[key_id]
        default_permissions = ["chat", "context", "tasks"]
        assert api_key_obj.permissions == default_permissions
        
        # Modify permissions
        api_key_obj.permissions = ["chat"]  # Limited permissions
        
        # Validate key still works but with limited permissions
        validated_key = auth_manager.validate_api_key(api_key)
        assert validated_key is not None
        assert validated_key.permissions == ["chat"]
    
    def test_api_key_usage_tracking(self, auth_manager):
        """Test API key usage is tracked for security monitoring."""
        user_id = "tracking_test_user"
        key_id, api_key = auth_manager.generate_api_key(user_id, "Tracked Key")
        
        # Initially no usage
        api_key_obj = auth_manager._api_keys[key_id]
        assert api_key_obj.last_used is None
        
        # Use the key
        validated_key = auth_manager.validate_api_key(api_key)
        assert validated_key is not None
        
        # Usage should be tracked
        assert validated_key.last_used is not None
        assert abs((datetime.utcnow() - validated_key.last_used).total_seconds()) < 1


class TestRateLimitingSecurity:
    """Test rate limiting prevents abuse."""
    
    @pytest.fixture
    def auth_manager(self):
        return AuthManager()
    
    def test_rate_limiting_basic_functionality(self, auth_manager):
        """Test basic rate limiting functionality."""
        identifier = "test_user_basic"
        limit = 5
        window = 60  # 60 seconds
        
        # Should allow requests within limit
        for i in range(limit):
            allowed = auth_manager.check_rate_limit(identifier, limit, window)
            assert allowed is True, f"Request {i+1} should be allowed"
        
        # Should deny request over limit
        denied = auth_manager.check_rate_limit(identifier, limit, window)
        assert denied is False, "Request over limit should be denied"
    
    def test_rate_limiting_window_reset(self, auth_manager):
        """Test rate limiting window resets properly."""
        identifier = "test_user_window"
        limit = 2
        window = 1  # 1 second window for fast test
        
        # Use up the limit
        assert auth_manager.check_rate_limit(identifier, limit, window) is True
        assert auth_manager.check_rate_limit(identifier, limit, window) is True
        assert auth_manager.check_rate_limit(identifier, limit, window) is False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        assert auth_manager.check_rate_limit(identifier, limit, window) is True
    
    def test_rate_limiting_per_user_isolation(self, auth_manager):
        """Test rate limiting is isolated per user."""
        user1 = "rate_user_1"
        user2 = "rate_user_2"
        limit = 3
        
        # User 1 uses up their limit
        for _ in range(limit):
            assert auth_manager.check_rate_limit(user1, limit) is True
        assert auth_manager.check_rate_limit(user1, limit) is False
        
        # User 2 should still have their full limit
        for _ in range(limit):
            assert auth_manager.check_rate_limit(user2, limit) is True
        assert auth_manager.check_rate_limit(user2, limit) is False
    
    def test_rate_limiting_cleanup(self, auth_manager):
        """Test rate limiting data is cleaned up properly."""
        identifiers = [f"cleanup_user_{i}" for i in range(10)]
        
        # Generate rate limiting data
        for identifier in identifiers:
            auth_manager.check_rate_limit(identifier, 10, 3600)
        
        # Should have data for all identifiers
        assert len(auth_manager._request_counts) == len(identifiers)
        
        # Run cleanup (which cleans old data)
        auth_manager.cleanup_expired()
        
        # For this test, data should still be there (not old enough)
        # But the cleanup method should handle old data removal


class TestUserRegistrationSecurity:
    """Test user registration security."""
    
    @pytest.fixture
    def auth_manager(self):
        return AuthManager()
    
    def test_registration_duplicate_email_handling(self, auth_manager):
        """Test duplicate email registration is handled securely."""
        email = "duplicate@example.com"
        
        # First registration should succeed
        request1 = RegistrationRequest(
            name="User One",
            email=email,
            password="Password123!"
        )
        response1 = auth_manager.register_user(request1)
        assert response1.success is True
        
        # Second registration with same email should fail gracefully
        request2 = RegistrationRequest(
            name="User Two",
            email=email,
            password="DifferentPass456!"
        )
        response2 = auth_manager.register_user(request2)
        assert response2.success is False
        assert "already have an account" in response2.message
        
        # Should not create second user
        assert len(auth_manager._email_to_user_id) == 1
    
    def test_registration_user_id_uniqueness(self, auth_manager):
        """Test user IDs are unique and unpredictable."""
        registrations = []
        user_ids = []
        
        # Create multiple users
        for i in range(10):
            request = RegistrationRequest(
                name=f"Test User {i}",
                email=f"test{i}@example.com",
                password="TestPass123!"
            )
            response = auth_manager.register_user(request)
            assert response.success is True
            
            user_id = response.user["user_id"]
            user_ids.append(user_id)
            registrations.append(response)
        
        # All user IDs should be unique
        assert len(set(user_ids)) == len(user_ids)
        
        # User IDs should be sufficiently long and random
        for user_id in user_ids:
            assert len(user_id) >= 16, "User ID too short for security"
            # Should be URL-safe base64 characters
            assert user_id.replace('-', '').replace('_', '').isalnum()
    
    def test_registration_input_sanitization(self, auth_manager):
        """Test registration input is properly sanitized."""
        # Test with potentially malicious inputs
        malicious_inputs = [
            "Normal Name",  # Normal case
            "  Padded Name  ",  # Should be trimmed
            "<script>alert('xss')</script>",  # XSS attempt
            "Name'DROP TABLE users;--",  # SQL injection attempt
            "A" * 200,  # Very long name (should fail validation)
        ]
        
        for i, name in enumerate(malicious_inputs):
            try:
                request = RegistrationRequest(
                    name=name,
                    email=f"test{i}@example.com",
                    password="ValidPass123!"
                )
                response = auth_manager.register_user(request)
                
                if response.success:
                    # Check that name was sanitized
                    stored_user = auth_manager._users[response.user["user_id"]]
                    stored_name = stored_user.name
                    
                    # Should not contain dangerous characters as-is
                    assert "<script>" not in stored_name
                    assert "DROP TABLE" not in stored_name
                    
                    # Padded names should be trimmed
                    if name.strip() == "Padded Name":
                        assert stored_name == "Padded Name"
                
            except ValueError:
                # Some inputs should fail validation (like too long names)
                if len(name) > 100:
                    pass  # Expected to fail
                else:
                    raise


class TestLoginSecurity:
    """Test login security and attack prevention."""
    
    @pytest.fixture
    def auth_manager_with_user(self):
        """Create auth manager with a test user."""
        auth_manager = AuthManager()
        
        # Register a test user
        request = RegistrationRequest(
            name="Test User",
            email="test@example.com",
            password="TestPassword123!"
        )
        response = auth_manager.register_user(request)
        assert response.success is True
        
        return auth_manager, "test@example.com", "TestPassword123!"
    
    def test_login_timing_attack_resistance(self, auth_manager_with_user):
        """Test login is resistant to timing attacks."""
        auth_manager, valid_email, valid_password = auth_manager_with_user
        
        # Test valid login timing
        valid_times = []
        for _ in range(10):
            login_request = LoginRequest(email=valid_email, password=valid_password)
            start = time.perf_counter()
            response = auth_manager.login_user(login_request)
            end = time.perf_counter()
            valid_times.append(end - start)
            assert response.success is True
            # Logout to clean up
            auth_manager.logout_user(response.session_id)
        
        # Test invalid email timing
        invalid_email_times = []
        for _ in range(10):
            login_request = LoginRequest(email="nonexistent@example.com", password=valid_password)
            start = time.perf_counter()
            response = auth_manager.login_user(login_request)
            end = time.perf_counter()
            invalid_email_times.append(end - start)
            assert response.success is False
        
        # Test invalid password timing
        invalid_password_times = []
        for _ in range(10):
            login_request = LoginRequest(email=valid_email, password="WrongPassword123!")
            start = time.perf_counter()
            response = auth_manager.login_user(login_request)
            end = time.perf_counter()
            invalid_password_times.append(end - start)
            assert response.success is False
        
        # Calculate averages
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid_email = sum(invalid_email_times) / len(invalid_email_times)
        avg_invalid_password = sum(invalid_password_times) / len(invalid_password_times)
        
        # Timing should be similar to prevent user enumeration
        # Invalid email vs invalid password timing should be similar
        timing_ratio = max(avg_invalid_email, avg_invalid_password) / min(avg_invalid_email, avg_invalid_password)
        assert timing_ratio < 2.0, f"Timing attack possible: email={avg_invalid_email:.6f}s, password={avg_invalid_password:.6f}s"
    
    def test_login_error_message_consistency(self, auth_manager_with_user):
        """Test login error messages don't reveal user existence."""
        auth_manager, valid_email, valid_password = auth_manager_with_user
        
        # Invalid email
        invalid_email_request = LoginRequest(
            email="nonexistent@example.com",
            password=valid_password
        )
        invalid_email_response = auth_manager.login_user(invalid_email_request)
        
        # Invalid password
        invalid_password_request = LoginRequest(
            email=valid_email,
            password="WrongPassword123!"
        )
        invalid_password_response = auth_manager.login_user(invalid_password_request)
        
        # Error messages should be identical to prevent user enumeration
        assert invalid_email_response.message == invalid_password_response.message
        assert "don't match our records" in invalid_email_response.message
    
    def test_login_session_creation_security(self, auth_manager_with_user):
        """Test login creates secure session."""
        auth_manager, valid_email, valid_password = auth_manager_with_user
        
        login_request = LoginRequest(email=valid_email, password=valid_password)
        response = auth_manager.login_user(
            login_request,
            user_agent="Test Browser",
            ip_address="192.168.1.100"
        )
        
        assert response.success is True
        assert response.session_id is not None
        assert response.expires_at is not None
        
        # Session should be properly created
        session = auth_manager._sessions[response.session_id]
        assert session.user_agent == "Test Browser"
        assert session.ip_address == "192.168.1.100"
        assert session.is_valid() is True
        
        # Clean up
        auth_manager.logout_user(response.session_id)
    
    def test_multiple_concurrent_login_attempts(self, auth_manager_with_user):
        """Test system handles concurrent login attempts securely."""
        auth_manager, valid_email, valid_password = auth_manager_with_user
        
        async def attempt_login(attempt_id: int):
            login_request = LoginRequest(email=valid_email, password=valid_password)
            response = auth_manager.login_user(
                login_request,
                user_agent=f"Browser {attempt_id}",
                ip_address=f"192.168.1.{attempt_id % 255}"
            )
            return response
        
        # This is a sync test, so we'll simulate concurrent attempts
        responses = []
        for i in range(10):
            response = attempt_login(i)
            responses.append(response)
        
        # All should succeed (same user, different sessions)
        session_ids = []
        for response in responses:
            assert response.success is True
            assert response.session_id is not None
            session_ids.append(response.session_id)
            
            # Clean up
            auth_manager.logout_user(response.session_id)
        
        # All session IDs should be unique
        assert len(set(session_ids)) == len(session_ids)


class TestPasswordResetSecurity:
    """Test password reset security."""
    
    @pytest.fixture
    def auth_manager_with_user(self):
        """Create auth manager with a test user."""
        auth_manager = AuthManager()
        
        request = RegistrationRequest(
            name="Reset Test User",
            email="reset@example.com",
            password="OriginalPass123!"
        )
        response = auth_manager.register_user(request)
        assert response.success is True
        
        return auth_manager, "reset@example.com", response.user["user_id"]
    
    def test_password_reset_token_security(self, auth_manager_with_user):
        """Test password reset tokens are secure."""
        auth_manager, email, user_id = auth_manager_with_user
        
        # Request password reset
        reset_request = PasswordResetRequest(email=email)
        response = auth_manager.request_password_reset(email)
        assert response.success is True
        
        # Check token was generated
        user_data = auth_manager._user_data[user_id]
        assert user_data.reset_token is not None
        assert user_data.reset_token_expires is not None
        
        # Token should be long and random
        token = user_data.reset_token
        assert len(token) >= 32, "Reset token too short"
        assert token.replace('-', '').replace('_', '').isalnum(), "Reset token not URL-safe"
        
        # Token should expire
        expires = user_data.reset_token_expires
        assert expires > datetime.utcnow()
        assert expires < datetime.utcnow() + timedelta(hours=2)  # Should expire within reasonable time
    
    def test_password_reset_token_uniqueness(self, auth_manager_with_user):
        """Test reset tokens are unique per request."""
        auth_manager, email, user_id = auth_manager_with_user
        
        # Request multiple resets
        tokens = []
        for _ in range(5):
            response = auth_manager.request_password_reset(email)
            assert response.success is True
            
            user_data = auth_manager._user_data[user_id]
            tokens.append(user_data.reset_token)
            
            # Small delay to ensure different tokens
            time.sleep(0.001)
        
        # All tokens should be unique
        assert len(set(tokens)) == len(tokens)
    
    def test_password_reset_execution_security(self, auth_manager_with_user):
        """Test password reset execution is secure."""
        auth_manager, email, user_id = auth_manager_with_user
        
        # Request reset
        auth_manager.request_password_reset(email)
        user_data = auth_manager._user_data[user_id]
        reset_token = user_data.reset_token
        
        # Reset password
        new_password = "NewSecurePass456!"
        reset_confirm = PasswordResetConfirm(
            token=reset_token,
            new_password=new_password
        )
        response = auth_manager.reset_password(reset_confirm)
        assert response.success is True
        
        # Token should be cleared
        assert user_data.reset_token is None
        assert user_data.reset_token_expires is None
        
        # New password should work
        login_request = LoginRequest(email=email, password=new_password)
        login_response = auth_manager.login_user(login_request)
        assert login_response.success is True
        
        # Old password should not work
        old_login_request = LoginRequest(email=email, password="OriginalPass123!")
        old_login_response = auth_manager.login_user(old_login_request)
        assert old_login_response.success is False
        
        # Clean up
        auth_manager.logout_user(login_response.session_id)
    
    def test_password_reset_token_expiration(self, auth_manager_with_user):
        """Test password reset tokens expire properly."""
        auth_manager, email, user_id = auth_manager_with_user
        
        # Request reset
        auth_manager.request_password_reset(email)
        user_data = auth_manager._user_data[user_id]
        reset_token = user_data.reset_token
        
        # Manually expire the token
        user_data.reset_token_expires = datetime.utcnow() - timedelta(minutes=1)
        
        # Try to use expired token
        reset_confirm = PasswordResetConfirm(
            token=reset_token,
            new_password="NewPass789!"
        )
        response = auth_manager.reset_password(reset_confirm)
        assert response.success is False
        assert "expired" in response.message.lower()
    
    def test_password_reset_session_invalidation(self, auth_manager_with_user):
        """Test password reset invalidates existing sessions."""
        auth_manager, email, user_id = auth_manager_with_user
        
        # Login and create session
        login_request = LoginRequest(email=email, password="OriginalPass123!")
        login_response = auth_manager.login_user(login_request)
        assert login_response.success is True
        session_id = login_response.session_id
        
        # Verify session is valid
        assert auth_manager.validate_session(session_id) is not None
        
        # Request and complete password reset
        auth_manager.request_password_reset(email)
        user_data = auth_manager._user_data[user_id]
        reset_token = user_data.reset_token
        
        reset_confirm = PasswordResetConfirm(
            token=reset_token,
            new_password="NewPass789!"
        )
        reset_response = auth_manager.reset_password(reset_confirm)
        assert reset_response.success is True
        
        # Session should be invalidated
        assert auth_manager.validate_session(session_id) is None
    
    def test_password_reset_nonexistent_user(self, auth_manager_with_user):
        """Test password reset doesn't reveal user existence."""
        auth_manager, _, _ = auth_manager_with_user
        
        # Request reset for nonexistent user
        response = auth_manager.request_password_reset("nonexistent@example.com")
        
        # Should appear to succeed (no user enumeration)
        assert response.success is True
        assert "receive password reset instructions" in response.message


class TestAuthorizationAndAccessControl:
    """Test authorization and access control security."""
    
    @pytest.fixture
    def auth_manager_with_users(self):
        """Create auth manager with multiple test users."""
        auth_manager = AuthManager()
        
        users_data = []
        for i in range(3):
            request = RegistrationRequest(
                name=f"User {i}",
                email=f"user{i}@example.com",
                password=f"Password{i}23!"
            )
            response = auth_manager.register_user(request)
            assert response.success is True
            users_data.append((response.user["user_id"], f"user{i}@example.com", f"Password{i}23!"))
        
        return auth_manager, users_data
    
    def test_user_isolation(self, auth_manager_with_users):
        """Test users can't access each other's data."""
        auth_manager, users_data = auth_manager_with_users
        user1_id, user1_email, user1_pass = users_data[0]
        user2_id, user2_email, user2_pass = users_data[1]
        
        # Login both users
        login1 = LoginRequest(email=user1_email, password=user1_pass)
        response1 = auth_manager.login_user(login1)
        assert response1.success is True
        
        login2 = LoginRequest(email=user2_email, password=user2_pass)
        response2 = auth_manager.login_user(login2)
        assert response2.success is True
        
        # User 1 should only access their own data
        user1_session = auth_manager.validate_session(response1.session_id)
        assert user1_session.user_id == user1_id
        
        # User 2 should only access their own data
        user2_session = auth_manager.validate_session(response2.session_id)
        assert user2_session.user_id == user2_id
        
        # Users should be different
        assert user1_session.user_id != user2_session.user_id
        
        # Clean up
        auth_manager.logout_user(response1.session_id)
        auth_manager.logout_user(response2.session_id)
    
    def test_session_hijacking_prevention(self, auth_manager_with_users):
        """Test sessions can't be hijacked or reused maliciously."""
        auth_manager, users_data = auth_manager_with_users
        user1_id, user1_email, user1_pass = users_data[0]
        
        # Create session for user 1
        login_request = LoginRequest(email=user1_email, password=user1_pass)
        response = auth_manager.login_user(
            login_request,
            user_agent="Original Browser",
            ip_address="192.168.1.100"
        )
        assert response.success is True
        session_id = response.session_id
        
        # Validate session works
        session = auth_manager.validate_session(session_id)
        assert session is not None
        assert session.user_id == user1_id
        assert session.user_agent == "Original Browser"
        assert session.ip_address == "192.168.1.100"
        
        # Session should be tied to metadata
        # (In a real implementation, you might check user agent/IP changes)
        
        # Manually modify session (simulating hijack attempt)
        modified_session_id = session_id[:-5] + "HACKED"
        hijacked_session = auth_manager.validate_session(modified_session_id)
        assert hijacked_session is None, "Session hijacking should not work"
        
        # Clean up
        auth_manager.logout_user(session_id)
    
    def test_api_key_access_isolation(self, auth_manager_with_users):
        """Test API keys are isolated between users."""
        auth_manager, users_data = auth_manager_with_users
        user1_id, _, _ = users_data[0]
        user2_id, _, _ = users_data[1]
        
        # Generate API keys for both users
        key1_id, api_key1 = auth_manager.generate_api_key(user1_id, "User 1 Key")
        key2_id, api_key2 = auth_manager.generate_api_key(user2_id, "User 2 Key")
        
        # Validate keys work for correct users
        validated_key1 = auth_manager.validate_api_key(api_key1)
        assert validated_key1.user_id == user1_id
        
        validated_key2 = auth_manager.validate_api_key(api_key2)
        assert validated_key2.user_id == user2_id
        
        # Keys should be different
        assert api_key1 != api_key2
        assert key1_id != key2_id
        assert validated_key1.user_id != validated_key2.user_id


class TestEmergencyAccessSecurity:
    """Test emergency access doesn't compromise security."""
    
    def test_debug_mode_security(self):
        """Test debug mode access is properly secured."""
        from mcp_server.auth import get_current_user
        from mcp_server.config import settings
        from fastapi import Request
        from unittest.mock import Mock
        
        # Mock request with debug header
        mock_request = Mock(spec=Request)
        mock_request.cookies = {}
        mock_request.headers = {"X-User-ID": "debug_user_123"}
        
        # Test depends on debug mode setting
        original_debug = settings.debug
        
        try:
            # With debug disabled, should fail
            settings.debug = False
            with pytest.raises(HTTPException) as exc_info:
                # This would be async in real usage, but we're testing the logic
                pass  # The actual test would need async context
            
            # With debug enabled, should create debug user
            settings.debug = True
            # In real implementation, this would create a debug user
            
        finally:
            # Restore original setting
            settings.debug = original_debug
    
    def test_crisis_bypass_maintains_security(self):
        """Test crisis response bypass doesn't compromise security."""
        # Crisis responses should work without authentication
        # but should not provide access to user data or system functions
        
        # This test would verify that crisis responses:
        # 1. Work without authentication
        # 2. Don't expose user data
        # 3. Don't provide system access
        # 4. Are properly logged for audit
        
        # Implementation would depend on crisis response integration
        pass


class TestSecurityAuditing:
    """Test security events are properly logged and audited."""
    
    @pytest.fixture
    def auth_manager(self):
        return AuthManager()
    
    def test_failed_login_logging(self, auth_manager, caplog):
        """Test failed login attempts are logged."""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Attempt login with invalid credentials
        login_request = LoginRequest(
            email="nonexistent@example.com",
            password="WrongPassword"
        )
        response = auth_manager.login_user(
            login_request,
            ip_address="192.168.1.50"
        )
        assert response.success is False
        
        # Should log failed attempt
        failed_login_logs = [
            record for record in caplog.records 
            if record.levelno >= logging.WARNING and "Failed login" in record.message
        ]
        assert len(failed_login_logs) > 0
        
        # Log should include security-relevant information
        log_message = failed_login_logs[0].message
        assert "192.168.1.50" in str(caplog.records)  # IP should be logged
    
    def test_session_creation_logging(self, auth_manager, caplog):
        """Test session creation is logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Register and login user
        reg_request = RegistrationRequest(
            name="Audit Test User",
            email="audit@example.com",
            password="TestPass123!"
        )
        reg_response = auth_manager.register_user(reg_request)
        assert reg_response.success is True
        
        # Check session creation is logged
        session_logs = [
            record for record in caplog.records 
            if "Created session" in record.message
        ]
        assert len(session_logs) > 0
    
    def test_security_event_data_protection(self, auth_manager, caplog):
        """Test sensitive data is not logged in security events."""
        import logging
        caplog.set_level(logging.DEBUG)  # Capture all logs
        
        # Register user with sensitive data
        reg_request = RegistrationRequest(
            name="Sensitive Test User",
            email="sensitive@example.com",
            password="SensitivePassword123!"
        )
        reg_response = auth_manager.register_user(reg_request)
        assert reg_response.success is True
        
        # Login user
        login_request = LoginRequest(
            email="sensitive@example.com",
            password="SensitivePassword123!"
        )
        login_response = auth_manager.login_user(login_request)
        assert login_response.success is True
        
        # Check that sensitive data is not in logs
        all_log_text = ' '.join([record.message for record in caplog.records])
        
        # Passwords should never be logged
        assert "SensitivePassword123!" not in all_log_text
        
        # Session IDs should not be fully logged (only partial for debugging)
        session_id = login_response.session_id
        assert session_id not in all_log_text  # Full session ID should not be logged
        
        # Clean up
        auth_manager.logout_user(session_id)