"""
Integration tests for GitHub Automation API endpoints

Tests the complete API integration with authentication, database,
and external service interactions.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from mcp_server.main import app
from mcp_server.database import Base
from mcp_server.models import User
from github_automation.models import GitHubIssue, GitHubAutomationAction, ActionStatus


@pytest.fixture
async def test_db():
    """Create test database."""
    # Use in-memory SQLite for testing
    DATABASE_URL = "sqlite+aiosqlite:///./test_github_automation.db"
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestingSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield TestingSessionLocal
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user(test_db):
    """Create test user."""
    async with test_db() as session:
        user = User(
            user_id="test-user-1",
            name="Test User",
            email="test@example.com"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def authenticated_client(test_user):
    """Create authenticated test client."""
    # Mock authentication
    def mock_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    client = TestClient(app)
    yield client
    
    # Clean up override
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def sample_github_issue(test_db):
    """Create sample GitHub issue for testing."""
    async with test_db() as session:
        issue = GitHubIssue(
            id="test-issue-1",
            github_issue_number=42,
            github_issue_id=123456,
            repository_owner="test_owner",
            repository_name="test_repo",
            title="Test Issue for Automation",
            status="open",
            author="developer",
            github_created_at=datetime.utcnow(),
            github_updated_at=datetime.utcnow(),
            automation_confidence="high",
            feature_completion_score=0.85
        )
        session.add(issue)
        await session.commit()
        await session.refresh(issue)
        return issue


class TestGitHubAutomationAPI:
    """Integration tests for GitHub automation API endpoints."""
    
    @pytest.mark.asyncio
    async def test_run_automation_cycle_endpoint(self, authenticated_client, test_db):
        """Test automation cycle trigger endpoint."""
        
        with patch('github_automation.automation_engine.GitHubAutomationEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.start_automation_cycle.return_value = {
                "cycle_id": "test-cycle-123",
                "duration_seconds": 5.2,
                "repository": "test_owner/test_repo",
                "execution_results": {
                    "total_actions": 3,
                    "successful_actions": 3
                }
            }
            mock_engine_class.return_value = mock_engine
            
            # Make API request
            response = authenticated_client.post(
                "/api/github/automation/run",
                json={
                    "owner": "test_owner",
                    "name": "test_repo",
                    "force_full_scan": False
                }
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
            assert data["repository"] == "test_owner/test_repo"
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_get_automation_status_endpoint(self, authenticated_client):
        """Test automation status retrieval endpoint."""
        
        with patch('github_automation.automation_engine.GitHubAutomationEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.get_automation_health.return_value = {
                "status": "healthy",
                "last_24_hours": {
                    "total_actions": 10,
                    "successful_actions": 9,
                    "success_rate": 0.9
                },
                "system_state": {
                    "running": False
                }
            }
            mock_engine_class.return_value = mock_engine
            
            # Make API request  
            response = authenticated_client.get("/api/github/automation/status")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "status" in data
            assert data["status"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_update_automation_config_endpoint(self, authenticated_client):
        """Test automation configuration update endpoint."""
        
        with patch('github_automation.automation_engine.GitHubAutomationEngine') as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine.config = None  # Will be updated
            mock_engine_class.return_value = mock_engine
            
            # Make API request
            response = authenticated_client.put(
                "/api/github/automation/config",
                json={
                    "max_concurrent_actions": 15,
                    "min_confidence_auto_close": 0.9,
                    "enable_auto_close": True,
                    "enable_rollbacks": True
                }
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["config"]["max_concurrent_actions"] == 15
            assert data["config"]["min_confidence_auto_close"] == 0.9
    
    @pytest.mark.asyncio
    async def test_get_repository_issues_endpoint(self, authenticated_client, test_db, sample_github_issue):
        """Test repository issues retrieval endpoint."""
        
        # Override database dependency
        app.dependency_overrides[get_database_session] = lambda: test_db()
        
        try:
            # Make API request
            response = authenticated_client.get(
                "/api/github/issues?owner=test_owner&name=test_repo&limit=10"
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "issues" in data
            assert "pagination" in data
            
            # Verify issue data
            issues = data["issues"]
            assert len(issues) > 0
            
            issue = issues[0]
            assert issue["github_issue_number"] == 42
            assert issue["title"] == "Test Issue for Automation"
            assert issue["status"] == "open"
            assert issue["automation_confidence"] == "high"
            
        finally:
            app.dependency_overrides.pop(get_database_session, None)
    
    @pytest.mark.asyncio
    async def test_get_issue_actions_endpoint(self, authenticated_client, test_db, sample_github_issue):
        """Test issue automation actions retrieval endpoint."""
        
        # Create test automation action
        async with test_db() as session:
            action = GitHubAutomationAction(
                id="test-action-1",
                issue_id=sample_github_issue.id,
                action_type="close_issue",
                status=ActionStatus.COMPLETED,
                confidence_score=0.9,
                reasoning="Feature completion detected",
                success=True,
                duration_ms=250.0
            )
            session.add(action)
            await session.commit()
        
        # Override database dependency
        app.dependency_overrides[get_database_session] = lambda: test_db()
        
        try:
            # Make API request
            response = authenticated_client.get(
                f"/api/github/issues/{sample_github_issue.id}/actions"
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["issue_id"] == sample_github_issue.id
            assert len(data["actions"]) == 1
            
            # Verify action data
            action_data = data["actions"][0]
            assert action_data["action_type"] == "close_issue"
            assert action_data["status"] == "completed"
            assert action_data["confidence_score"] == 0.9
            assert action_data["success"] is True
            
        finally:
            app.dependency_overrides.pop(get_database_session, None)
    
    @pytest.mark.asyncio
    async def test_create_rollback_transaction_endpoint(self, authenticated_client, test_db):
        """Test rollback transaction creation endpoint."""
        
        with patch('github_automation.rollback_manager.RollbackManager') as mock_rollback_class:
            mock_rollback = AsyncMock()
            mock_rollback.create_rollback_transaction.return_value = "rollback-tx-123"
            mock_rollback_class.return_value = mock_rollback
            
            # Make API request
            response = authenticated_client.post(
                "/api/github/rollback/create",
                json={
                    "action_ids": ["action-1", "action-2"],
                    "reason": "User requested rollback due to incorrect closure"
                }
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["transaction_id"] == "rollback-tx-123"
            assert data["action_count"] == 2
            assert data["status"] == "executing"
    
    @pytest.mark.asyncio
    async def test_github_webhook_endpoint(self, authenticated_client):
        """Test GitHub webhook processing endpoint."""
        
        with patch('github_automation.webhook_handler.WebhookHandler') as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler.process_webhook.return_value = {
                "success": True,
                "delivery_id": "test-delivery-123",
                "event_type": "issues",
                "handlers_executed": 1
            }
            mock_handler_class.return_value = mock_handler
            
            # Mock webhook payload
            webhook_payload = {
                "action": "opened",
                "issue": {
                    "number": 43,
                    "title": "New test issue",
                    "state": "open"
                },
                "repository": {
                    "owner": {"login": "test_owner"},
                    "name": "test_repo"
                }
            }
            
            # Make API request with webhook headers
            response = authenticated_client.post(
                "/api/github/webhooks/github",
                json=webhook_payload,
                headers={
                    "X-GitHub-Delivery": "test-delivery-123",
                    "X-GitHub-Event": "issues"
                }
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["delivery_id"] == "test-delivery-123"
    
    @pytest.mark.asyncio
    async def test_automation_metrics_endpoint(self, authenticated_client, test_db):
        """Test automation metrics retrieval endpoint."""
        
        # Create test automation actions for metrics
        async with test_db() as session:
            # Create a completed action
            action1 = GitHubAutomationAction(
                id="test-action-1",
                issue_id="test-issue-1",
                action_type="close_issue",
                status=ActionStatus.COMPLETED,
                confidence_score=0.9,
                success=True,
                duration_ms=150.0,
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
            
            # Create a failed action
            action2 = GitHubAutomationAction(
                id="test-action-2", 
                issue_id="test-issue-2",
                action_type="label_issue",
                status=ActionStatus.FAILED,
                confidence_score=0.7,
                success=False,
                error_message="API rate limit exceeded",
                created_at=datetime.utcnow() - timedelta(hours=2)
            )
            
            session.add_all([action1, action2])
            await session.commit()
        
        # Override database dependency
        app.dependency_overrides[get_database_session] = lambda: test_db()
        
        try:
            # Make API request
            response = authenticated_client.get("/api/github/metrics/summary?hours=24")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # Verify metrics structure
            summary = data["summary"]
            assert "total_actions" in summary
            assert "successful_actions" in summary
            assert "failed_actions" in summary
            assert "success_rate" in summary
            
            # Verify action type breakdown
            assert "by_action_type" in data
            
        finally:
            app.dependency_overrides.pop(get_database_session, None)
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, authenticated_client):
        """Test GitHub automation health check endpoint."""
        
        # Make API request
        response = authenticated_client.get("/api/github/health")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "github_automation"
        assert "features" in data
        
        # Verify all expected features are reported
        features = data["features"]
        assert features["automation_engine"] is True
        assert features["webhook_processing"] is True
        assert features["rollback_management"] is True
        assert features["audit_logging"] is True
        assert features["feature_detection"] is True
    
    @pytest.mark.asyncio 
    async def test_unauthorized_access(self, test_db):
        """Test that endpoints require authentication."""
        
        # Create unauthenticated client
        client = TestClient(app)
        
        # Test various endpoints
        endpoints_to_test = [
            ("POST", "/api/github/automation/run"),
            ("GET", "/api/github/automation/status"),
            ("PUT", "/api/github/automation/config"),
            ("GET", "/api/github/issues"),
            ("POST", "/api/github/rollback/create"),
            ("GET", "/api/github/metrics/summary")
        ]
        
        for method, endpoint in endpoints_to_test:
            if method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            else:
                response = client.get(endpoint)
            
            # Should require authentication
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_input_validation(self, authenticated_client):
        """Test API input validation."""
        
        # Test invalid repository request
        response = authenticated_client.post(
            "/api/github/automation/run",
            json={
                "owner": "",  # Empty owner
                "name": "test_repo"
            }
        )
        assert response.status_code == 422  # Validation error
        
        # Test invalid config update
        response = authenticated_client.put(
            "/api/github/automation/config",
            json={
                "max_concurrent_actions": -1,  # Invalid negative value
                "min_confidence_auto_close": 1.5  # Invalid confidence > 1.0
            }
        )
        assert response.status_code == 422  # Validation error
        
        # Test invalid rollback request
        response = authenticated_client.post(
            "/api/github/rollback/create",
            json={
                "action_ids": [],  # Empty action IDs
                "reason": ""  # Empty reason
            }
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_error_handling(self, authenticated_client):
        """Test API error handling."""
        
        with patch('github_automation.automation_engine.GitHubAutomationEngine') as mock_engine_class:
            # Mock engine to raise an exception
            mock_engine_class.side_effect = Exception("GitHub API unavailable")
            
            # Make API request
            response = authenticated_client.post(
                "/api/github/automation/run",
                json={
                    "owner": "test_owner",
                    "name": "test_repo"
                }
            )
            
            # Verify error response
            assert response.status_code == 500
            data = response.json()
            assert "Failed to start automation cycle" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_pagination_functionality(self, authenticated_client, test_db):
        """Test API pagination functionality."""
        
        # Create multiple test issues
        async with test_db() as session:
            issues = []
            for i in range(25):
                issue = GitHubIssue(
                    id=f"test-issue-{i}",
                    github_issue_number=i + 1,
                    github_issue_id=100000 + i,
                    repository_owner="test_owner",
                    repository_name="test_repo",
                    title=f"Test Issue {i + 1}",
                    status="open",
                    author="developer",
                    github_created_at=datetime.utcnow() - timedelta(days=i),
                    github_updated_at=datetime.utcnow() - timedelta(hours=i)
                )
                issues.append(issue)
            
            session.add_all(issues)
            await session.commit()
        
        # Override database dependency
        app.dependency_overrides[get_database_session] = lambda: test_db()
        
        try:
            # Test first page
            response = authenticated_client.get(
                "/api/github/issues?owner=test_owner&name=test_repo&limit=10&offset=0"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["issues"]) == 10
            assert data["pagination"]["total"] == 25
            assert data["pagination"]["has_more"] is True
            
            # Test second page
            response = authenticated_client.get(
                "/api/github/issues?owner=test_owner&name=test_repo&limit=10&offset=10"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["issues"]) == 10
            assert data["pagination"]["has_more"] is True
            
            # Test last page
            response = authenticated_client.get(
                "/api/github/issues?owner=test_owner&name=test_repo&limit=10&offset=20"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["issues"]) == 5  # Remaining issues
            assert data["pagination"]["has_more"] is False
            
        finally:
            app.dependency_overrides.pop(get_database_session, None)