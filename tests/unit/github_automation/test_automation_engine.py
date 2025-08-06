"""
Unit tests for GitHub Automation Engine

Comprehensive test suite covering core automation functionality,
feature detection, and performance characteristics.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from github_automation.automation_engine import (
    GitHubAutomationEngine, AutomationConfig
)
from github_automation.models import (
    GitHubIssue, GitHubAutomationAction, FeatureDetection,
    ActionStatus, AutomationAction, IssueStatus, ConfidenceLevel
)


class TestAutomationEngine:
    """Test cases for GitHubAutomationEngine."""
    
    @pytest.fixture
    def automation_config(self):
        """Create test automation configuration."""
        return AutomationConfig(
            max_concurrent_actions=5,
            min_confidence_auto_close=0.8,
            min_confidence_auto_label=0.6,
            enable_auto_close=True,
            enable_auto_label=True,
            max_actions_per_run=50
        )
    
    @pytest.fixture
    def mock_github_client(self):
        """Create mock GitHub client."""
        mock_client = AsyncMock()
        mock_client.get_repository_issues.return_value = [
            {
                'id': 123456,
                'number': 42,
                'title': 'Implement MCP Client Integration',
                'state': 'open',
                'body': 'Need to implement MCP client for universal tool integration',
                'labels': [{'name': 'enhancement'}, {'name': 'integration'}],
                'created_at': '2024-01-15T10:00:00Z',
                'updated_at': '2024-01-16T12:00:00Z',
                'user': {'login': 'developer'},
                'assignees': []
            }
        ]
        return mock_client
    
    @pytest.fixture
    def mock_feature_detector(self):
        """Create mock feature detector."""
        mock_detector = AsyncMock()
        mock_detector.analyze_issue_completion.return_value = {
            'features_detected': 1,
            'detections': [
                {
                    'feature_name': 'MCP Client Implementation',
                    'confidence_score': 0.9,
                    'completion_status': 'completed',
                    'evidence': {
                        'code_files': ['src/mcp_client/client.py', 'src/mcp_client/auth.py'],
                        'test_files': ['tests/test_mcp_client.py'],
                        'commits': [
                            {'message': 'Complete MCP client implementation', 'hash': 'abc123'}
                        ]
                    },
                    'false_positive_score': 0.1,
                    'detection_method': 'multi_factor_analysis'
                }
            ],
            'analysis_duration_ms': 150.0
        }
        return mock_detector
    
    @pytest.fixture
    async def automation_engine(self, automation_config, mock_github_client, mock_feature_detector):
        """Create automation engine with mocked dependencies."""
        with patch('github_automation.automation_engine.GitHubAPIClient') as mock_client_class:
            mock_client_class.return_value = mock_github_client
            
            with patch('github_automation.automation_engine.FeatureDetector') as mock_detector_class:
                mock_detector_class.return_value = mock_feature_detector
                
                engine = GitHubAutomationEngine(
                    github_token="test_token",
                    config=automation_config
                )
                
                return engine
    
    @pytest.mark.asyncio
    async def test_automation_cycle_basic_flow(self, automation_engine, mock_github_client, mock_feature_detector):
        """Test basic automation cycle execution."""
        
        # Mock database operations
        with patch('github_automation.automation_engine.get_database_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            
            # Execute automation cycle
            results = await automation_engine.start_automation_cycle(
                repository_owner="test_owner",
                repository_name="test_repo"
            )
            
            # Verify results structure
            assert 'cycle_id' in results
            assert 'duration_seconds' in results
            assert 'repository' in results
            assert results['repository'] == "test_owner/test_repo"
            
            # Verify GitHub client was called
            mock_github_client.get_repository_issues.assert_called_once()
            
            # Verify feature detection was triggered
            mock_feature_detector.analyze_issue_completion.assert_called()
    
    @pytest.mark.asyncio
    async def test_sync_issues_from_github(self, automation_engine, mock_github_client):
        """Test GitHub issue synchronization."""
        
        with patch('github_automation.automation_engine.get_database_session'):
            # Test issue sync
            sync_results = await automation_engine._sync_issues_from_github(
                "test_owner", "test_repo", force_full_scan=False
            )
            
            # Verify sync results
            assert 'total_issues_fetched' in sync_results
            assert 'new_issues' in sync_results
            assert 'updated_issues' in sync_results
            assert 'sync_duration_seconds' in sync_results
            
            # Verify GitHub API was called with correct parameters
            mock_github_client.get_repository_issues.assert_called_with(
                "test_owner", "test_repo", 
                since=None, state="all", per_page=100
            )
    
    @pytest.mark.asyncio
    async def test_feature_completion_analysis(self, automation_engine, mock_feature_detector):
        """Test feature completion analysis."""
        
        # Mock database with test issues
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_issue = GitHubIssue(
            id="test-issue-1",
            github_issue_number=42,
            github_issue_id=123456,
            repository_owner="test_owner",
            repository_name="test_repo",
            title="Test Issue",
            status=IssueStatus.OPEN,
            author="developer",
            github_created_at=datetime.utcnow(),
            github_updated_at=datetime.utcnow()
        )
        mock_result.scalars.return_value.all.return_value = [mock_issue]
        mock_session.execute.return_value = mock_result
        
        with patch('github_automation.automation_engine.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Execute analysis
            analysis_results = await automation_engine._analyze_feature_completions(
                "test_owner", "test_repo"
            )
            
            # Verify analysis results
            assert 'total_issues_analyzed' in analysis_results
            assert 'features_detected' in analysis_results
            assert 'high_confidence_completions' in analysis_results
            assert 'completion_correlations' in analysis_results
            
            # Verify feature detector was called
            mock_feature_detector.analyze_issue_completion.assert_called_with(
                mock_issue, "test_owner", "test_repo"
            )
    
    @pytest.mark.asyncio
    async def test_automation_action_generation(self, automation_engine):
        """Test automation action generation based on feature analysis."""
        
        # Mock database with feature detections
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_issue = GitHubIssue(
            id="test-issue-1",
            github_issue_number=42,
            github_issue_id=123456,
            repository_owner="test_owner",
            repository_name="test_repo",
            title="Test Issue",
            status=IssueStatus.OPEN,
            author="developer",
            automation_confidence=ConfidenceLevel.HIGH,
            github_created_at=datetime.utcnow(),
            github_updated_at=datetime.utcnow()
        )
        mock_result.scalars.return_value.all.return_value = [mock_issue]
        mock_session.execute.return_value = mock_result
        
        with patch('github_automation.automation_engine.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            with patch.object(automation_engine, '_create_automation_action') as mock_create_action:
                mock_create_action.return_value = None
                
                # Execute action generation
                action_results = await automation_engine._generate_automation_actions(
                    "test_owner", "test_repo"
                )
                
                # Verify action generation results
                assert 'close_actions' in action_results
                assert 'label_actions' in action_results
                assert 'comment_actions' in action_results
                assert 'total_actions' in action_results
                
                # Verify close action was created for high-confidence completion
                if automation_engine.config.enable_auto_close:
                    mock_create_action.assert_called()
    
    @pytest.mark.asyncio
    async def test_automation_action_execution(self, automation_engine, mock_github_client):
        """Test execution of automation actions."""
        
        # Mock pending actions
        mock_action = GitHubAutomationAction(
            id="test-action-1",
            issue_id="test-issue-1",
            action_type=AutomationAction.CLOSE_ISSUE,
            status=ActionStatus.PENDING,
            confidence_score=0.9,
            reasoning="Feature completion detected with high confidence",
            evidence={"code_files": ["test.py"]}
        )
        
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_action]
        mock_session.execute.return_value = mock_result
        
        with patch('github_automation.automation_engine.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            with patch.object(automation_engine, '_execute_single_action') as mock_execute:
                mock_execute.return_value = {'success': True, 'rate_limited': False}
                
                # Execute actions
                execution_results = await automation_engine._execute_automation_actions(
                    "test_owner", "test_repo"
                )
                
                # Verify execution results
                assert 'total_actions' in execution_results
                assert 'successful_actions' in execution_results
                assert 'failed_actions' in execution_results
                
                # Verify action execution was attempted
                mock_execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, automation_engine):
        """Test rate limiting integration with action execution."""
        
        # Mock rate limiter to deny requests
        automation_engine.rate_limiter.can_make_request = AsyncMock(return_value=False)
        
        mock_action = GitHubAutomationAction(
            id="test-action-1",
            issue_id="test-issue-1",
            action_type=AutomationAction.CLOSE_ISSUE,
            status=ActionStatus.PENDING,
            confidence_score=0.9,
            reasoning="Test action",
            evidence={}
        )
        
        semaphore = asyncio.Semaphore(1)
        
        # Execute single action
        result = await automation_engine._execute_single_action(mock_action, semaphore)
        
        # Verify rate limiting was respected
        assert not result['success']
        assert result['rate_limited']
        assert result['error'] == 'Rate limited'
    
    @pytest.mark.asyncio
    async def test_webhook_event_processing(self, automation_engine):
        """Test webhook event processing."""
        
        webhook_data = {
            'action': 'opened',
            'issue': {
                'number': 42,
                'title': 'Test Issue',
                'state': 'open'
            },
            'repository': {
                'owner': {'login': 'test_owner'},
                'name': 'test_repo',
                'full_name': 'test_owner/test_repo'
            }
        }
        
        headers = {
            'X-GitHub-Delivery': 'test-delivery-id',
            'X-GitHub-Event': 'issues'
        }
        
        with patch.object(automation_engine, '_store_webhook_event') as mock_store:
            mock_store.return_value = None
            
            with patch.object(automation_engine, '_process_issues_webhook') as mock_process:
                mock_process.return_value = {'processed': True}
                
                # Process webhook
                result = await automation_engine.process_webhook_event(webhook_data, headers)
                
                # Verify webhook processing
                assert 'processed' in result
                mock_store.assert_called_once_with(webhook_data, headers)
    
    @pytest.mark.asyncio
    async def test_automation_health_monitoring(self, automation_engine):
        """Test automation system health monitoring."""
        
        with patch('github_automation.automation_engine.get_database_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            
            # Mock successful automation actions
            mock_action = GitHubAutomationAction(
                id="test-action-1",
                action_type=AutomationAction.CLOSE_ISSUE,
                status=ActionStatus.COMPLETED,
                success=True,
                duration_ms=100.0,
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
            
            # Get health status
            health_status = await automation_engine.get_automation_health()
            
            # Verify health status structure
            assert 'status' in health_status
            assert 'last_24_hours' in health_status
            assert 'rate_limiting' in health_status
            assert 'configuration' in health_status
            assert 'system_state' in health_status
            
            # Verify configuration is included
            config = health_status['configuration']
            assert config['max_concurrent_actions'] == automation_engine.config.max_concurrent_actions
            assert config['auto_close_enabled'] == automation_engine.config.enable_auto_close
    
    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, automation_engine):
        """Test performance metrics tracking during operations."""
        
        # Verify initial metrics
        initial_metrics = automation_engine.performance_metrics
        assert 'total_processed' in initial_metrics
        assert 'successful_actions' in initial_metrics
        assert 'api_calls_made' in initial_metrics
        
        # Mock a successful operation
        with patch.object(automation_engine, '_sync_issues_from_github') as mock_sync:
            mock_sync.return_value = {
                'total_issues_fetched': 10,
                'new_issues': 2,
                'api_calls_made': 3
            }
            
            with patch.object(automation_engine, '_analyze_feature_completions') as mock_analyze:
                mock_analyze.return_value = {
                    'total_issues_analyzed': 10,
                    'features_detected': 1
                }
                
                with patch.object(automation_engine, '_generate_automation_actions') as mock_generate:
                    mock_generate.return_value = {'total_actions': 1}
                    
                    with patch.object(automation_engine, '_execute_automation_actions') as mock_execute:
                        mock_execute.return_value = {
                            'total_actions': 1,
                            'successful_actions': 1
                        }
                        
                        # Execute cycle
                        await automation_engine.start_automation_cycle("test_owner", "test_repo")
                        
                        # Verify metrics were updated
                        metrics = automation_engine.performance_metrics
                        assert metrics['total_processed'] > initial_metrics['total_processed']
    
    def test_automation_config_validation(self):
        """Test automation configuration validation."""
        
        # Test valid configuration
        valid_config = AutomationConfig(
            max_concurrent_actions=10,
            min_confidence_auto_close=0.85,
            enable_auto_close=True
        )
        assert valid_config.max_concurrent_actions == 10
        assert valid_config.min_confidence_auto_close == 0.85
        
        # Test configuration with extreme values
        extreme_config = AutomationConfig(
            max_concurrent_actions=1,
            min_confidence_auto_close=1.0,
            max_actions_per_run=1
        )
        assert extreme_config.max_concurrent_actions == 1
        assert extreme_config.min_confidence_auto_close == 1.0
        
    def test_batch_processing_utility(self, automation_engine):
        """Test batch processing utility function."""
        
        # Test batch creation
        items = list(range(25))
        batch_size = 10
        
        batches = list(automation_engine._batch_items(items, batch_size))
        
        # Verify batch structure
        assert len(batches) == 3  # 25 items in batches of 10
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5  # Remaining items
        
        # Verify all items are included
        all_batched_items = []
        for batch in batches:
            all_batched_items.extend(batch)
        
        assert sorted(all_batched_items) == sorted(items)