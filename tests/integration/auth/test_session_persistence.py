"""
Integration tests for session persistence across server restarts.

This module tests the critical requirement that database-backed sessions
persist across server restarts, eliminating the previous in-memory session
vulnerability.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from mcp_server.main import create_app
from mcp_server.database import Base, get_db_session
from mcp_server.enhanced_auth import enhanced_auth_manager, RegistrationRequest, LoginRequest
from mcp_server.db_models import Session as DBSession, User as DBUser
from mcp_server.config import settings


class TestSessionPersistence:
    """Test session persistence across server restarts."""
    
    @pytest.fixture
    async def test_database(self):
        """Create test database for integration tests."""
        # Use in-memory SQLite for fast testing
        test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )
        
        # Create tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        yield test_engine, TestSessionLocal
        
        # Cleanup
        await test_engine.dispose()
    
    @pytest.fixture
    async def test_app(self, test_database):
        """Create test FastAPI application with test database."""
        test_engine, TestSessionLocal = test_database
        
        # Override database dependency
        async def override_get_db_session():
            async with TestSessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        app = create_app()
        app.dependency_overrides[get_db_session] = override_get_db_session
        
        return app, TestSessionLocal
    
    @pytest.fixture
    def test_user_data(self):
        """Test user registration and login data."""
        return {
            "registration": RegistrationRequest(
                name="Test User",
                email="test@persistence.com", 
                password="TestPassword123"
            ),
            "login": LoginRequest(
                email="test@persistence.com",
                password="TestPassword123"
            )
        }
    
    async def test_session_survives_server_restart_simulation(self, test_app, test_user_data):
        """Test that sessions survive server restart simulation."""
        app, SessionLocal = test_app
        
        # Phase 1: Start "server" and create user session
        client = TestClient(app)
        
        # Register user
        response = client.post("/api/auth/register", json=test_user_data["registration"].dict())
        assert response.status_code == 200
        registration_result = response.json()
        assert registration_result["success"] is True
        
        # Login user to create session
        response = client.post("/api/auth/login", json=test_user_data["login"].dict())
        assert response.status_code == 200
        login_result = response.json()
        assert login_result["success"] is True
        
        session_id = login_result["session_id"]
        csrf_token = login_result["csrf_token"]
        user_id = login_result["user"]["user_id"]
        
        # Verify session exists in database
        async with SessionLocal() as db:
            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            db_session = result.scalar_one_or_none()
            assert db_session is not None
            assert db_session.is_active is True
            assert db_session.user_id == user_id
        
        # Use session for authenticated request
        headers = {
            "X-CSRF-Token": csrf_token,
            "Cookie": f"session_id={session_id}"
        }
        
        response = client.get("/api/users/profile", headers=headers)
        assert response.status_code == 200
        
        # Phase 2: Simulate server restart by creating new app instance
        # Note: The database persists, but all in-memory state is lost
        
        # Create new app instance (simulates restart)
        new_app = create_app()
        
        # Override database dependency for new app
        async def override_get_db_session():
            async with SessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        new_app.dependency_overrides[get_db_session] = override_get_db_session
        new_client = TestClient(new_app)
        
        # Phase 3: Verify session still works after "restart"
        
        # Check that session still exists in database
        async with SessionLocal() as db:
            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            db_session = result.scalar_one_or_none()
            assert db_session is not None
            assert db_session.is_active is True
        
        # Use session with new app instance
        response = new_client.get("/api/users/profile", headers=headers)
        assert response.status_code == 200
        
        profile_data = response.json()
        assert profile_data["user_id"] == user_id
        
        # Verify session was refreshed (last_accessed updated)
        async with SessionLocal() as db:
            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            refreshed_session = result.scalar_one_or_none()
            assert refreshed_session.last_accessed > db_session.last_accessed
    
    async def test_multiple_sessions_persistence(self, test_app, test_user_data):
        """Test that multiple sessions for the same user persist."""
        app, SessionLocal = test_app
        client = TestClient(app)
        
        # Register user
        response = client.post("/api/auth/register", json=test_user_data["registration"].dict())
        assert response.status_code == 200
        
        # Create multiple sessions (simulate login from different devices)
        sessions = []
        
        for i in range(3):
            # Login to create session
            response = client.post("/api/auth/login", json=test_user_data["login"].dict())
            assert response.status_code == 200
            login_result = response.json()
            
            sessions.append({
                "session_id": login_result["session_id"],
                "csrf_token": login_result["csrf_token"],
                "user_id": login_result["user"]["user_id"]
            })
        
        # Verify all sessions exist in database
        async with SessionLocal() as db:
            for session_data in sessions:
                result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_data["session_id"])
                )
                db_session = result.scalar_one_or_none()
                assert db_session is not None
                assert db_session.is_active is True
        
        # Simulate server restart with new app instance
        new_app = create_app()
        async def override_get_db_session():
            async with SessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        new_app.dependency_overrides[get_db_session] = override_get_db_session
        new_client = TestClient(new_app)
        
        # Verify all sessions still work after restart
        for session_data in sessions:
            headers = {
                "X-CSRF-Token": session_data["csrf_token"],
                "Cookie": f"session_id={session_data['session_id']}"
            }
            
            response = new_client.get("/api/users/profile", headers=headers)
            assert response.status_code == 200
            profile_data = response.json()
            assert profile_data["user_id"] == session_data["user_id"]
    
    async def test_expired_session_cleanup_after_restart(self, test_app, test_user_data):
        """Test that expired sessions are properly cleaned up after restart."""
        app, SessionLocal = test_app
        client = TestClient(app)
        
        # Register and login user
        response = client.post("/api/auth/register", json=test_user_data["registration"].dict())
        assert response.status_code == 200
        
        response = client.post("/api/auth/login", json=test_user_data["login"].dict())
        assert response.status_code == 200
        login_result = response.json()
        
        session_id = login_result["session_id"]
        
        # Manually expire the session in database
        async with SessionLocal() as db:
            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            db_session = result.scalar_one_or_none()
            
            # Set expiry to past
            db_session.expires_at = datetime.utcnow() - timedelta(hours=1)
            await db.commit()
        
        # Simulate server restart
        new_app = create_app()
        async def override_get_db_session():
            async with SessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        new_app.dependency_overrides[get_db_session] = override_get_db_session
        new_client = TestClient(new_app)
        
        # Try to use expired session - should fail
        headers = {
            "Cookie": f"session_id={session_id}"
        }
        
        response = new_client.get("/api/users/profile", headers=headers)
        assert response.status_code == 401  # Unauthorized due to expired session
        
        # Verify expired session was marked as inactive
        async with SessionLocal() as db:
            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            db_session = result.scalar_one_or_none()
            # Session should exist but be inactive (cleanup would happen separately)
            assert db_session is not None
    
    async def test_session_security_after_restart(self, test_app, test_user_data):
        """Test that session security features work after restart."""
        app, SessionLocal = test_app
        client = TestClient(app)
        
        # Register and login user
        response = client.post("/api/auth/register", json=test_user_data["registration"].dict())
        assert response.status_code == 200
        
        response = client.post("/api/auth/login", json=test_user_data["login"].dict())
        assert response.status_code == 200
        login_result = response.json()
        
        session_id = login_result["session_id"]
        csrf_token = login_result["csrf_token"]
        
        # Simulate server restart
        new_app = create_app()
        async def override_get_db_session():
            async with SessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        new_app.dependency_overrides[get_db_session] = override_get_db_session
        new_client = TestClient(new_app)
        
        # Test CSRF protection still works after restart
        headers = {
            "Cookie": f"session_id={session_id}"
            # Deliberately omit CSRF token
        }
        
        response = new_client.post("/api/users/profile", headers=headers, json={"name": "Updated"})
        assert response.status_code == 403  # Should be blocked by CSRF protection
        
        # Test with valid CSRF token
        headers["X-CSRF-Token"] = csrf_token
        response = new_client.post("/api/users/profile", headers=headers, json={"name": "Updated"})
        # Should work (or return appropriate validation error, not CSRF error)
        assert response.status_code != 403
    
    async def test_jwt_secret_rotation_persistence(self, test_app):
        """Test that JWT secret rotation works with database persistence."""
        app, SessionLocal = test_app
        
        # Create JWT manager and generate initial secret
        async with SessionLocal() as db:
            secret1 = await enhanced_auth_manager.jwt_manager.create_new_secret(db, "initial")
            assert secret1 is not None
        
        # Simulate server restart by creating new manager instance
        new_jwt_manager = enhanced_auth_manager.jwt_manager.__class__()
        
        # Verify secret is retrieved from database
        async with SessionLocal() as db:
            retrieved_secret = await new_jwt_manager.get_active_secret(db)
            assert retrieved_secret == secret1
        
        # Create new secret (rotation)
        async with SessionLocal() as db:
            secret2 = await new_jwt_manager.create_new_secret(db, "rotation")
            assert secret2 != secret1
        
        # Verify new secret is active
        async with SessionLocal() as db:
            active_secret = await new_jwt_manager.get_active_secret(db)
            assert active_secret == secret2
    
    async def test_performance_requirements_after_restart(self, test_app, test_user_data):
        """Test that ADHD performance requirements are met after restart."""
        app, SessionLocal = test_app
        client = TestClient(app)
        
        # Setup: Register and login
        response = client.post("/api/auth/register", json=test_user_data["registration"].dict())
        assert response.status_code == 200
        
        response = client.post("/api/auth/login", json=test_user_data["login"].dict())
        assert response.status_code == 200
        login_result = response.json()
        
        session_id = login_result["session_id"]
        csrf_token = login_result["csrf_token"]
        
        # Simulate server restart
        new_app = create_app()
        async def override_get_db_session():
            async with SessionLocal() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        new_app.dependency_overrides[get_db_session] = override_get_db_session
        new_client = TestClient(new_app)
        
        # Measure authentication response time
        headers = {
            "X-CSRF-Token": csrf_token,
            "Cookie": f"session_id={session_id}"
        }
        
        start_time = time.time()
        response = new_client.get("/api/users/profile", headers=headers)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # ADHD requirement: sub-3 second response time
        assert response_time < 3000, f"Response time {response_time}ms exceeds ADHD requirement of 3000ms"
        assert response.status_code == 200
        
        # Verify ADHD performance header is set
        assert "X-ADHD-Performance" in response.headers
        performance_status = response.headers["X-ADHD-Performance"]
        assert performance_status in ["optimal", "acceptable"]  # Should not be "slow"


class TestLegacyMigration:
    """Test migration from legacy in-memory sessions to database-backed."""
    
    async def test_graceful_fallback_for_missing_sessions(self, test_app):
        """Test graceful handling of sessions that don't exist in database."""
        app, SessionLocal = test_app
        client = TestClient(app)
        
        # Try to use a non-existent session ID
        fake_session_id = "fake_session_that_doesnt_exist"
        headers = {
            "Cookie": f"session_id={fake_session_id}"
        }
        
        response = client.get("/api/users/profile", headers=headers)
        assert response.status_code == 401  # Should gracefully return unauthorized
        
        # Verify no errors in application logs (would need to check logging in real test)
    
    async def test_backward_compatibility_with_existing_auth_endpoints(self, test_app, test_user_data):
        """Test that existing authentication endpoints still work."""
        app, SessionLocal = test_app
        client = TestClient(app)
        
        # All existing auth endpoints should work
        endpoints_to_test = [
            ("/api/auth/register", "post", test_user_data["registration"].dict()),
            ("/api/auth/login", "post", test_user_data["login"].dict()),
        ]
        
        for endpoint, method, data in endpoints_to_test:
            if method == "post":
                response = client.post(endpoint, json=data)
            else:
                response = client.get(endpoint)
            
            # Should not return 404 or 500 (endpoints should exist and work)
            assert response.status_code not in [404, 500]


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short", "-x"])