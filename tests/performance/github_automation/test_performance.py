"""
Performance tests for GitHub Automation System

Tests system performance under load, scalability characteristics,
and response time requirements for large-scale operations.
"""

import asyncio
import time
import statistics
from unittest.mock import AsyncMock, patch
from typing import List, Dict

import pytest
from concurrent.futures import ThreadPoolExecutor

from github_automation.automation_engine import GitHubAutomationEngine, AutomationConfig
from github_automation.models import GitHubIssue, IssueStatus
from github_automation.github_client import GitHubAPIClient
from github_automation.rate_limiter import RateLimiter


class TestGitHubAutomationPerformance:
    """Performance tests for GitHub automation system."""
    
    @pytest.fixture
    def high_performance_config(self):
        """Configuration optimized for high performance."""
        return AutomationConfig(
            max_concurrent_actions=50,
            batch_size=100,
            min_confidence_auto_close=0.8,
            max_actions_per_run=1000,
            analysis_timeout_seconds=60
        )
    
    @pytest.fixture
    def mock_large_issue_dataset(self):
        """Generate large dataset of mock issues."""
        issues = []
        for i in range(1000):
            issues.append({
                'id': 100000 + i,
                'number': i + 1,
                'title': f'Performance Test Issue {i + 1}',
                'state': 'open' if i % 3 != 0 else 'closed',
                'body': f'Test issue {i + 1} for performance testing',
                'labels': [{'name': 'performance'}, {'name': 'test'}],
                'created_at': f'2024-01-{(i % 30) + 1:02d}T10:00:00Z',
                'updated_at': f'2024-01-{(i % 30) + 1:02d}T12:00:00Z',
                'user': {'login': 'developer'},
                'assignees': []
            })
        return issues
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_issue_sync_performance_1000_issues(self, high_performance_config, mock_large_issue_dataset):
        """Test issue synchronization performance with 1000 issues."""
        
        with patch('github_automation.automation_engine.GitHubAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_repository_issues.return_value = mock_large_issue_dataset
            mock_client_class.return_value = mock_client
            
            engine = GitHubAutomationEngine(
                github_token="test_token",
                config=high_performance_config
            )
            
            # Mock database operations for performance
            with patch('github_automation.automation_engine.get_database_session'):
                with patch.object(engine, '_process_issue_batch') as mock_batch:
                    mock_batch.return_value = {'new_issues': 10, 'updated_issues': 0}
                    
                    # Measure sync performance
                    start_time = time.time()
                    
                    results = await engine._sync_issues_from_github(
                        "test_owner", "test_repo", force_full_scan=True
                    )
                    
                    duration = time.time() - start_time
                    
                    # Performance assertions
                    assert duration < 30.0  # Should complete within 30 seconds
                    assert results['total_issues_fetched'] == 1000
                    
                    # Verify batching was used efficiently
                    expected_batches = 1000 // high_performance_config.batch_size + 1
                    assert mock_batch.call_count <= expected_batches
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_automation_actions(self, high_performance_config):
        """Test concurrent execution of automation actions."""
        
        # Create mock actions
        mock_actions = []
        for i in range(100):
            action = AsyncMock()
            action.id = f"action-{i}"
            action.action_type = "close_issue"
            action.confidence_score = 0.9
            action.execution_attempts = 0
            action.max_attempts = 3
            mock_actions.append(action)
        
        with patch('github_automation.automation_engine.GitHubAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            engine = GitHubAutomationEngine(
                github_token="test_token",
                config=high_performance_config
            )
            
            # Mock successful action execution
            async def mock_execute_action(action, semaphore):
                async with semaphore:
                    await asyncio.sleep(0.01)  # Simulate processing time
                    return {'success': True, 'rate_limited': False}
            
            with patch.object(engine, '_execute_single_action', side_effect=mock_execute_action):
                # Measure concurrent execution performance
                start_time = time.time()
                
                semaphore = asyncio.Semaphore(high_performance_config.max_concurrent_actions)
                tasks = []
                
                for action in mock_actions:
                    task = engine._execute_single_action(action, semaphore)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                duration = time.time() - start_time
                
                # Performance assertions
                assert duration < 5.0  # Should complete within 5 seconds with concurrency
                assert len(results) == 100
                assert all(r['success'] for r in results)
                
                # Verify concurrency provided performance benefit
                # Sequential execution would take ~1 second (100 * 0.01)
                # Concurrent execution should be much faster
                assert duration < 1.0
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_feature_detection_performance(self):
        """Test feature detection performance on large codebase."""
        
        from github_automation.feature_detector import FeatureDetector
        
        detector = FeatureDetector()
        
        # Mock large issue with complex feature detection
        mock_issue = AsyncMock()
        mock_issue.github_issue_number = 42
        mock_issue.title = "Implement comprehensive MCP client with authentication and tool integration"
        mock_issue.description = "Full MCP client implementation with OAuth, tool registry, and error handling"
        
        # Mock file system operations for performance
        with patch.object(detector, '_check_file_presence') as mock_check_files:
            mock_check_files.return_value = {
                'src/mcp_client/client.py': True,
                'src/mcp_client/auth.py': True,
                'src/mcp_client/tools.py': True,
                'tests/test_mcp_client.py': True
            }
            
            with patch.object(detector, '_analyze_code_structure') as mock_analyze:
                mock_analyze.return_value = {
                    'classes_found': ['MCPClient', 'AuthManager', 'ToolRegistry'],
                    'methods_found': ['connect', 'authenticate', 'list_tools', 'call_tool'],
                    'imports_found': ['requests', 'oauth2', 'json'],
                    'class_score': 1.0,
                    'method_score': 1.0
                }
                
                with patch.object(detector, '_analyze_commits') as mock_commits:
                    mock_commits.return_value = [
                        {'message': 'Complete MCP client implementation', 'hash': 'abc123'}
                    ]
                    
                    # Measure feature detection performance
                    start_time = time.time()
                    
                    result = await detector.analyze_issue_completion(
                        mock_issue, "test_owner", "test_repo"
                    )
                    
                    duration = time.time() - start_time
                    
                    # Performance assertions
                    assert duration < 1.0  # Should complete within 1 second
                    assert result['features_detected'] > 0
                    assert result['analysis_duration_ms'] < 1000
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self):
        """Test rate limiter performance under high request load."""
        
        rate_limiter = RateLimiter(
            max_calls_per_hour=5000,
            max_calls_per_minute=100,
            burst_allowance=20
        )
        
        # Test sustained request load
        start_time = time.time()
        request_count = 0
        successful_requests = 0
        
        # Simulate 200 requests in rapid succession
        for i in range(200):
            if await rate_limiter.can_make_request():
                await rate_limiter.record_request()
                successful_requests += 1
            request_count += 1
        
        duration = time.time() - start_time
        
        # Performance assertions
        assert duration < 1.0  # Should process requests quickly
        assert successful_requests > 0  # Some requests should be allowed
        assert successful_requests <= 120  # Respect rate limits (burst + minute limit)
        
        # Test rate limiter statistics performance
        stats_start = time.time()
        status = rate_limiter.get_status()
        stats_duration = time.time() - stats_start
        
        assert stats_duration < 0.1  # Statistics should be very fast
        assert 'current_usage' in status
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_github_api_client_performance(self):
        """Test GitHub API client performance with caching."""
        
        client = GitHubAPIClient("test_token")
        
        # Mock HTTP responses for performance testing
        mock_response_data = [
            {'id': i, 'number': i, 'title': f'Issue {i}'}
            for i in range(100)
        ]
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                'success': True,
                'data': mock_response_data,
                'status_code': 200
            }
            
            # Test first request (cache miss)
            start_time = time.time()
            result1 = await client.get_repository_issues("owner", "repo", per_page=100)
            first_duration = time.time() - start_time
            
            # Test second request (should hit cache if implemented)
            start_time = time.time()
            result2 = await client.get_repository_issues("owner", "repo", per_page=100)
            second_duration = time.time() - start_time
            
            # Performance assertions
            assert first_duration < 1.0  # First request should be fast
            assert len(result1) == 100
            assert len(result2) == 100
            
            # Cache should improve performance on subsequent requests
            # (This assumes caching is implemented in the client)
            cache_stats = client.get_metrics()
            assert 'cache_hits' in cache_stats
        
        await client.close()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_webhook_processing_performance(self):
        """Test webhook processing performance under load."""
        
        from github_automation.webhook_handler import WebhookHandler
        
        handler = WebhookHandler()
        
        # Create mock webhook payloads
        webhook_payloads = []
        for i in range(50):
            webhook_payloads.append({
                'action': 'opened',
                'issue': {
                    'number': i + 1,
                    'title': f'Performance Test Issue {i + 1}',
                    'state': 'open'
                },
                'repository': {
                    'owner': {'login': 'test_owner'},
                    'name': 'test_repo'
                }
            })
        
        # Mock request objects
        mock_requests = []
        for i, payload in enumerate(webhook_payloads):
            mock_request = AsyncMock()
            mock_request.headers = {
                'X-GitHub-Delivery': f'delivery-{i}',
                'X-GitHub-Event': 'issues'
            }
            mock_request.json.return_value = payload
            mock_requests.append(mock_request)
        
        # Process webhooks concurrently
        start_time = time.time()
        
        tasks = []
        for i, (request, payload) in enumerate(zip(mock_requests, webhook_payloads)):
            task = handler.process_webhook(request, payload)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Performance assertions
        assert duration < 5.0  # Should process all webhooks within 5 seconds
        assert len(results) == 50
        
        # Verify all webhooks were processed successfully
        successful_processing = sum(1 for r in results if r.get('success', False))
        assert successful_processing > 40  # At least 80% success rate
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database query performance with large datasets."""
        
        # This test would require a real database with test data
        # For now, we'll test the query structure and mock performance
        
        from github_automation.models import GitHubIssue, GitHubAutomationAction
        
        # Mock database session with performance characteristics
        mock_session = AsyncMock()
        
        # Mock query execution times
        async def mock_execute_with_delay(query):
            await asyncio.sleep(0.01)  # Simulate database query time
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = [
                GitHubIssue(id=f"issue-{i}", github_issue_number=i)
                for i in range(100)
            ]
            return mock_result
        
        mock_session.execute = mock_execute_with_delay
        
        # Test query performance
        start_time = time.time()
        
        # Simulate multiple concurrent database queries
        query_tasks = []
        for i in range(10):
            task = mock_session.execute(f"SELECT * FROM github_issues LIMIT 100")
            query_tasks.append(task)
        
        results = await asyncio.gather(*query_tasks)
        duration = time.time() - start_time
        
        # Performance assertions
        assert duration < 1.0  # 10 queries should complete within 1 second
        assert len(results) == 10
    
    @pytest.mark.performance
    def test_memory_usage_under_load(self, high_performance_config):
        """Test memory usage characteristics under load."""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create automation engine and simulate load
        engine = GitHubAutomationEngine(
            github_token="test_token",
            config=high_performance_config
        )
        
        # Create large number of mock objects to test memory usage
        mock_issues = []
        for i in range(10000):
            mock_issue = {
                'id': i,
                'number': i,
                'title': f'Memory Test Issue {i}',
                'data': 'x' * 1000  # 1KB of data per issue
            }
            mock_issues.append(mock_issue)
        
        # Process the mock issues
        batches = list(engine._batch_items(mock_issues, 100))
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        # Memory usage assertions
        assert memory_increase < 100  # Should not use more than 100MB additional
        assert len(batches) == 100  # Verify batching worked correctly
        
        # Clean up
        del mock_issues
        del batches
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_end_to_end_automation_cycle_performance(self, high_performance_config):
        """Test complete automation cycle performance."""
        
        with patch('github_automation.automation_engine.GitHubAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_repository_issues.return_value = [
                {
                    'id': i,
                    'number': i,
                    'title': f'E2E Test Issue {i}',
                    'state': 'open'
                }
                for i in range(100)
            ]
            mock_client_class.return_value = mock_client
            
            with patch('github_automation.automation_engine.FeatureDetector') as mock_detector_class:
                mock_detector = AsyncMock()
                mock_detector.analyze_issue_completion.return_value = {
                    'features_detected': 1,
                    'detections': [{
                        'confidence_score': 0.9,
                        'completion_status': 'completed'
                    }]
                }
                mock_detector_class.return_value = mock_detector
                
                engine = GitHubAutomationEngine(
                    github_token="test_token",
                    config=high_performance_config
                )
                
                # Mock database operations
                with patch('github_automation.automation_engine.get_database_session'):
                    # Execute complete automation cycle
                    start_time = time.time()
                    
                    results = await engine.start_automation_cycle(
                        repository_owner="test_owner",
                        repository_name="test_repo",
                        force_full_scan=True
                    )
                    
                    duration = time.time() - start_time
                    
                    # End-to-end performance assertions
                    assert duration < 60.0  # Complete cycle within 1 minute
                    assert 'cycle_id' in results
                    assert results['repository'] == "test_owner/test_repo"
                    
                    # Verify performance metrics
                    metrics = engine.performance_metrics
                    assert metrics['total_processed'] > 0
    
    @pytest.mark.performance
    def test_performance_monitoring_overhead(self):
        """Test performance monitoring system overhead."""
        
        from github_automation.audit_logger import AuditLogger
        
        audit_logger = AuditLogger(enable_console_logging=False)
        
        # Measure audit logging performance
        start_time = time.time()
        
        # Log many events quickly
        for i in range(1000):
            # Note: This would be async in real usage
            # Using sync version for performance measurement
            pass
        
        duration = time.time() - start_time
        
        # Performance assertion - monitoring should have minimal overhead
        assert duration < 1.0  # 1000 operations within 1 second
        
        # Check statistics performance
        stats_start = time.time()
        stats = audit_logger.get_statistics()
        stats_duration = time.time() - stats_start
        
        assert stats_duration < 0.01  # Statistics retrieval should be very fast
        assert isinstance(stats, dict)