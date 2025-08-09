"""
Performance tests for ADHD-specific authentication requirements.

This module tests that the enhanced authentication system meets the critical
ADHD user experience requirements:
- Sub-3 second response times
- Crisis support access regardless of auth state
- Minimal cognitive load for auth failures
- Persistent sessions to avoid re-authentication interruptions
"""
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List
import httpx
from fastapi.testclient import TestClient

from mcp_server.main import create_app
from mcp_server.enhanced_auth import RegistrationRequest, LoginRequest
from mcp_server.config import settings


class TestADHDAuthPerformance:
    """Test ADHD-specific performance requirements for authentication."""
    
    @pytest.fixture
    def test_app(self):
        """Create test application."""
        return create_app()
    
    @pytest.fixture
    def test_user_data(self):
        """Test user data for performance tests."""
        return {
            "registration": {
                "name": "Performance Test User",
                "email": "perf@test.com",
                "password": "TestPass123"
            },
            "login": {
                "email": "perf@test.com", 
                "password": "TestPass123"
            }
        }
    
    async def test_registration_response_time_adhd_requirement(self, test_app, test_user_data):
        """Test that user registration meets ADHD response time requirements."""
        client = TestClient(test_app)
        
        # Measure registration response time
        start_time = time.time()
        response = client.post("/api/auth/register", json=test_user_data["registration"])
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # ADHD Requirement: Sub-3 second response time
        assert response_time_ms < 3000, f"Registration took {response_time_ms:.2f}ms, exceeds ADHD limit of 3000ms"
        assert response.status_code == 200
        
        # Verify ADHD performance header is set correctly
        if "X-ADHD-Performance" in response.headers:
            performance_status = response.headers["X-ADHD-Performance"]
            if response_time_ms < 1000:
                assert performance_status == "optimal"
            elif response_time_ms < 3000:
                assert performance_status == "acceptable" 
            else:
                assert performance_status == "slow"
    
    async def test_login_response_time_adhd_requirement(self, test_app, test_user_data):
        """Test that user login meets ADHD response time requirements."""
        client = TestClient(test_app)
        
        # First register user
        response = client.post("/api/auth/register", json=test_user_data["registration"])
        assert response.status_code == 200
        
        # Measure login response time
        start_time = time.time()
        response = client.post("/api/auth/login", json=test_user_data["login"])
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # ADHD Requirement: Sub-3 second response time
        assert response_time_ms < 3000, f"Login took {response_time_ms:.2f}ms, exceeds ADHD limit of 3000ms"
        assert response.status_code == 200
        
        # Login should be even faster than registration (no bcrypt hashing)
        assert response_time_ms < 2000, f"Login should be under 2s for ADHD users, took {response_time_ms:.2f}ms"
    
    async def test_session_validation_response_time(self, test_app, test_user_data):
        """Test that session validation is very fast for ADHD users."""
        client = TestClient(test_app)
        
        # Setup: Register and login to get session
        client.post("/api/auth/register", json=test_user_data["registration"])
        login_response = client.post("/api/auth/login", json=test_user_data["login"])
        login_data = login_response.json()
        
        session_id = login_data["session_id"]
        csrf_token = login_data["csrf_token"]
        
        headers = {
            "X-CSRF-Token": csrf_token,
            "Cookie": f"session_id={session_id}"
        }
        
        # Measure session validation time (authenticated request)
        start_time = time.time()
        response = client.get("/api/users/profile", headers=headers)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Session validation should be very fast (under 1 second)
        assert response_time_ms < 1000, f"Session validation took {response_time_ms:.2f}ms, should be under 1000ms"
        assert response.status_code == 200
    
    async def test_concurrent_authentication_performance(self, test_app):
        """Test authentication performance under concurrent load."""
        client = TestClient(test_app)
        
        # Create multiple test users for concurrent testing
        test_users = []
        for i in range(10):
            user_data = {
                "name": f"Concurrent User {i}",
                "email": f"concurrent{i}@test.com",
                "password": "TestPass123"
            }
            test_users.append(user_data)
            
            # Register users
            response = client.post("/api/auth/register", json=user_data)
            assert response.status_code == 200
        
        # Concurrent login test
        def login_user(user_data):
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            start_time = time.time()
            response = client.post("/api/auth/login", json=login_data)
            end_time = time.time()
            return {
                "response_time": (end_time - start_time) * 1000,
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
        
        # Execute concurrent logins
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login_user, user) for user in test_users]
            results = [future.result() for future in futures]
        
        # Analyze results
        response_times = [r["response_time"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        
        # All logins should succeed
        assert success_count == len(test_users), f"Only {success_count}/{len(test_users)} concurrent logins succeeded"
        
        # Average response time should be acceptable for ADHD users
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 3000, f"Average concurrent login time {avg_response_time:.2f}ms exceeds ADHD limit"
        
        # 95th percentile should also be acceptable (no user waits too long)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        assert p95_response_time < 5000, f"95th percentile response time {p95_response_time:.2f}ms too high"
    
    async def test_crisis_support_bypass_performance(self, test_app):
        """Test that crisis support bypass is fast and reliable."""
        client = TestClient(test_app)
        
        # Crisis message that should trigger bypass
        crisis_message = {
            "message": "I'm having thoughts of suicide and need help immediately",
            "urgent": True
        }
        
        # Measure crisis support access time (no authentication)
        start_time = time.time()
        response = client.post("/chat", json=crisis_message)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Crisis support should be VERY fast (under 500ms)
        assert response_time_ms < 500, f"Crisis support took {response_time_ms:.2f}ms, should be under 500ms"
        
        # Should not be blocked by authentication
        assert response.status_code != 401, "Crisis support should not be blocked by authentication"
    
    async def test_auth_failure_cognitive_load(self, test_app):
        """Test that authentication failures have minimal cognitive load."""
        client = TestClient(test_app)
        
        # Test various auth failure scenarios
        auth_failures = [
            {
                "name": "Invalid email format",
                "data": {"email": "invalid-email", "password": "test123"},
                "expected_keywords": ["email", "format", "valid"]
            },
            {
                "name": "Weak password", 
                "data": {"email": "test@example.com", "password": "123"},
                "expected_keywords": ["password", "8 characters", "letter", "number"]
            },
            {
                "name": "Wrong credentials",
                "data": {"email": "nonexistent@example.com", "password": "TestPass123"},
                "expected_keywords": ["don't match", "double-check", "reset"]
            }
        ]
        
        for failure_case in auth_failures:
            start_time = time.time()
            response = client.post("/api/auth/login", json=failure_case["data"])
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Even failures should be fast
            assert response_time_ms < 2000, f"{failure_case['name']} took {response_time_ms:.2f}ms"
            
            # Check ADHD-friendly error messages
            response_data = response.json()
            assert "message" in response_data
            
            error_message = response_data["message"].lower()
            
            # Should contain helpful keywords
            has_helpful_keywords = any(keyword in error_message for keyword in failure_case["expected_keywords"])
            assert has_helpful_keywords, f"Error message lacks ADHD-friendly guidance: {response_data['message']}"
            
            # Should not be overly technical or blame-heavy
            blame_words = ["invalid", "incorrect", "wrong", "bad", "error", "failed"]
            blame_count = sum(1 for word in blame_words if word in error_message)
            assert blame_count <= 1, f"Error message too blame-heavy for ADHD users: {response_data['message']}"
    
    async def test_session_persistence_reduces_auth_friction(self, test_app, test_user_data):
        """Test that persistent sessions reduce authentication friction for ADHD users."""
        client = TestClient(test_app)
        
        # Register and login
        client.post("/api/auth/register", json=test_user_data["registration"])
        login_response = client.post("/api/auth/login", json=test_user_data["login"])
        login_data = login_response.json()
        
        session_id = login_data["session_id"]
        csrf_token = login_data["csrf_token"]
        
        # Simulate multiple requests over time (hyperfocus session)
        requests_count = 20
        response_times = []
        
        headers = {
            "X-CSRF-Token": csrf_token,
            "Cookie": f"session_id={session_id}"
        }
        
        for i in range(requests_count):
            start_time = time.time()
            response = client.get("/api/users/profile", headers=headers)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            # Each request should succeed without re-authentication
            assert response.status_code == 200, f"Request {i+1} failed with status {response.status_code}"
            
            # Response time should remain consistent (no re-auth overhead)
            assert response_time < 1000, f"Request {i+1} took {response_time:.2f}ms, too slow for hyperfocus"
            
            # Small delay to simulate real usage
            time.sleep(0.1)
        
        # Verify session consistency (no degradation over time)
        first_half_avg = statistics.mean(response_times[:10])
        second_half_avg = statistics.mean(response_times[10:])
        
        # Second half should not be significantly slower (session should not degrade)
        degradation_ratio = second_half_avg / first_half_avg
        assert degradation_ratio < 1.5, f"Session performance degraded by {degradation_ratio:.2f}x over time"
    
    async def test_memory_efficient_session_management(self, test_app):
        """Test that session management is memory efficient for ADHD users with many sessions."""
        # This test would create many sessions and verify memory usage
        # For now, we'll test that creating many sessions doesn't slow down significantly
        
        client = TestClient(test_app)
        
        # Create multiple sessions (simulate user logging in from different devices)
        sessions = []
        response_times = []
        
        base_user = {
            "name": "Memory Test User",
            "email": "memory@test.com",
            "password": "TestPass123"
        }
        
        # Register user once
        client.post("/api/auth/register", json=base_user)
        
        # Create multiple sessions
        for i in range(10):
            start_time = time.time()
            response = client.post("/api/auth/login", json={
                "email": base_user["email"],
                "password": base_user["password"]
            })
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])
        
        # Verify no significant performance degradation with multiple sessions
        first_login_time = response_times[0]
        last_login_time = response_times[-1]
        
        degradation_ratio = last_login_time / first_login_time
        assert degradation_ratio < 2.0, f"Login performance degraded {degradation_ratio:.2f}x with multiple sessions"
        
        # All sessions should still be valid
        for i, session_id in enumerate(sessions):
            headers = {"Cookie": f"session_id={session_id}"}
            response = client.get("/api/users/profile", headers=headers)
            assert response.status_code == 200, f"Session {i+1} became invalid"


class TestADHDAuthAccessibility:
    """Test ADHD-specific accessibility features in authentication."""
    
    @pytest.fixture
    def test_app(self):
        return create_app()
    
    async def test_clear_progress_indicators(self, test_app):
        """Test that auth processes provide clear progress indicators."""
        client = TestClient(test_app)
        
        # Registration should provide clear feedback
        response = client.post("/api/auth/register", json={
            "name": "Progress Test User",
            "email": "progress@test.com", 
            "password": "TestPass123"
        })
        
        response_data = response.json()
        
        # Should have clear success message
        assert "success" in response_data
        assert "message" in response_data
        
        # Message should be encouraging and clear
        message = response_data["message"]
        assert "welcome" in message.lower() or "created" in message.lower()
        assert len(message) > 10, "Message should be descriptive enough for ADHD users"
    
    async def test_helpful_error_recovery(self, test_app):
        """Test that auth errors provide helpful recovery suggestions."""
        client = TestClient(test_app)
        
        # Test password reset suggestion on login failure
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        response_data = response.json()
        error_message = response_data.get("message", "").lower()
        
        # Should suggest password reset
        recovery_keywords = ["reset", "password", "forgot", "help"]
        has_recovery_suggestion = any(keyword in error_message for keyword in recovery_keywords)
        assert has_recovery_suggestion, f"Error message should suggest recovery: {response_data.get('message')}"
        
        # Should not be overwhelming
        assert len(error_message) < 200, "Error message too long for ADHD users"
    
    async def test_distraction_resistant_timeouts(self, test_app, test_user_data):
        """Test that sessions have reasonable timeouts for ADHD users."""
        client = TestClient(test_app)
        
        # Register and login
        client.post("/api/auth/register", json=test_user_data["registration"])
        login_response = client.post("/api/auth/login", json=test_user_data["login"])
        login_data = login_response.json()
        
        # Check that session expiry is reasonable (not too short for ADHD users)
        if "expires_at" in login_data:
            from datetime import datetime
            expires_at = datetime.fromisoformat(login_data["expires_at"].replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
            
            session_duration = (expires_at - now).total_seconds() / 3600  # Hours
            
            # Should be at least 4 hours (hyperfocus sessions can be long)
            assert session_duration >= 4, f"Session duration {session_duration:.1f}h too short for ADHD users"
            
            # Should not be excessively long (security concern)
            assert session_duration <= 48, f"Session duration {session_duration:.1f}h too long for security"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])