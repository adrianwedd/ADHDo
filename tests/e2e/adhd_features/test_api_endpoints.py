"""
End-to-end tests for ADHD API endpoints.

Tests the full API functionality including authentication, request/response
processing, and integration with all ADHD features through HTTP endpoints.
"""
import pytest
import asyncio
from httpx import AsyncClient
from datetime import datetime
from unittest.mock import Mock, patch

from mcp_server.main import app
from mcp_server.auth import create_access_token
from mcp_server.db_models import User


class TestADHDAPIEndpoints:
    """End-to-end tests for ADHD API endpoints."""
    
    @pytest.fixture
    def test_user_token(self):
        """Create test user and authentication token."""
        test_user = User(
            user_id="test_adhd_user",
            name="Test ADHD User",
            email="test@example.com",
            is_active=True
        )
        
        token = create_access_token({"sub": test_user.user_id})
        return token, test_user
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Authentication headers for API requests."""
        token, _ = test_user_token
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_enhanced_chat_endpoint(self, auth_headers):
        """Test enhanced chat endpoint with full ADHD support."""
        request_data = {
            "message": "I've been working on this task for hours and feel overwhelmed",
            "task_focus": "Complete project report",
            "nudge_tier": "gentle",
            "energy_level": 0.3,
            "urgency_level": 0.7,
            "enable_patterns": True,
            "enable_adaptations": True,
            "enable_executive_support": True
        }
        
        # Mock the enhanced cognitive loop
        with patch('adhd.enhanced_cognitive_loop.enhanced_cognitive_loop') as mock_loop:
            from adhd.enhanced_cognitive_loop import EnhancedCognitiveLoopResult
            from mcp_server.llm_client import LLMResponse
            
            mock_result = EnhancedCognitiveLoopResult(
                success=True,
                response=LLMResponse(
                    text="I understand you're feeling overwhelmed. Let's break this down into smaller steps.",
                    source="llm",
                    confidence=0.8,
                    model_used="gpt-4"
                ),
                actions_taken=['pattern_detection', 'cognitive_load_reduction'],
                cognitive_load=0.8,
                processing_time_ms=250.0,
                detected_patterns=[
                    {
                        'type': 'overwhelm',
                        'severity': 'high', 
                        'confidence': 0.85,
                        'intervention_recommended': True
                    }
                ],
                adaptations_applied=[
                    {
                        'type': 'cognitive_load_reduction',
                        'priority': 'high',
                        'reasoning': 'User showing signs of overwhelm'
                    }
                ],
                executive_function_support={
                    'task_breakdown': {
                        'subtasks': [
                            {'title': 'Gather research materials', 'time_estimate': 15},
                            {'title': 'Create outline', 'time_estimate': 10}
                        ],
                        'estimated_time': 25
                    }
                },
                intervention_recommendations=[
                    {
                        'type': 'overwhelm_intervention',
                        'urgency': 8,
                        'description': 'High overwhelm detected - immediate support recommended'
                    }
                ]
            )
            
            mock_loop.process_user_input.return_value = mock_result
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/adhd/chat/enhanced",
                    json=request_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data['success'] is True
                assert data['message'] == mock_result.response.text
                assert len(data['patterns_detected']) == 1
                assert data['patterns_detected'][0]['type'] == 'overwhelm'
                assert len(data['adaptations_applied']) == 1
                assert 'task_breakdown' in data['executive_support']
                assert data['cognitive_load'] == 0.8
    
    @pytest.mark.asyncio
    async def test_pattern_analysis_endpoint(self, auth_headers):
        """Test pattern analysis endpoint."""
        with patch('adhd.pattern_engine.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.get_pattern_summary.return_value = {
                'adhd_subtype': 'combined',
                'pattern_counts': {'hyperfocus': 5, 'overwhelm': 3},
                'recent_patterns': [
                    {'type': 'hyperfocus', 'severity': 'moderate', 'timestamp': datetime.utcnow().isoformat()}
                ],
                'total_patterns_detected': 8
            }
            mock_get_engine.return_value = mock_engine
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/adhd/patterns/analysis",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'analysis' in data
                assert data['analysis']['adhd_subtype'] == 'combined'
                assert data['analysis']['total_patterns_detected'] == 8
                assert len(data['analysis']['recent_patterns']) == 1
    
    @pytest.mark.asyncio
    async def test_adhd_subtype_classification_endpoint(self, auth_headers):
        """Test ADHD subtype classification endpoint."""
        with patch('adhd.pattern_engine.get_pattern_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.classify_adhd_subtype.return_value = Mock(value='inattentive')
            mock_get_engine.return_value = mock_engine
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/adhd/patterns/subtype-classification",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data['adhd_subtype'] == 'inattentive'
                assert 'classification_timestamp' in data
    
    @pytest.mark.asyncio
    async def test_user_profile_endpoints(self, auth_headers):
        """Test user profile GET and PUT endpoints."""
        # Mock profile manager
        with patch('adhd.user_profile.profile_manager') as mock_manager:
            mock_profile = Mock()
            mock_profile.dict.return_value = {
                'user_id': 'test_adhd_user',
                'adhd_subtype': 'combined',
                'cognitive_load_preference': 'adaptive',
                'hyperfocus_tendency': 0.6
            }
            mock_profile.last_updated = datetime.utcnow()
            
            mock_manager.get_or_create_profile.return_value = mock_profile
            mock_manager.get_personalized_settings.return_value = {
                'cognitive_load': {'max_context_items': 8},
                'interface': {'complexity': 'moderate'}
            }
            mock_manager.update_user_preferences.return_value = True
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Test GET profile
                response = await client.get(
                    "/adhd/profile",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'profile' in data
                assert 'personalized_settings' in data
                assert data['profile']['adhd_subtype'] == 'combined'
                
                # Test PUT profile update
                update_data = {
                    "cognitive_load_preference": "minimal",
                    "interaction_style": "direct",
                    "interface_complexity": "simple",
                    "nudge_methods": ["web", "telegram"],
                    "privacy_settings": {
                        "learning_enabled": False
                    }
                }
                
                response = await client.put(
                    "/adhd/profile",
                    json=update_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data['success'] is True
                assert 'cognitive_load_preference' in data['updated_preferences']
    
    @pytest.mark.asyncio
    async def test_task_breakdown_endpoint(self, auth_headers):
        """Test task breakdown endpoint."""
        with patch('adhd.executive_function.task_breakdown_engine') as mock_engine:
            mock_breakdown = Mock()
            mock_breakdown.original_task = "Write project report"
            mock_breakdown.subtasks = [
                {'title': 'Research phase', 'time_estimate': 30},
                {'title': 'Writing phase', 'time_estimate': 60},
                {'title': 'Review phase', 'time_estimate': 15}
            ]
            mock_breakdown.estimated_total_time = 105
            mock_breakdown.complexity_level.value = 'medium'
            mock_breakdown.executive_functions_required = [Mock(value='planning')]
            mock_breakdown.potential_obstacles = ['Getting started', 'Staying focused']
            mock_breakdown.success_strategies = ['Use timer', 'Take breaks']
            mock_breakdown.energy_requirements = {'mental': 0.7, 'physical': 0.3}
            
            mock_engine.breakdown_task.return_value = mock_breakdown
            
            request_data = {
                "task_description": "Write project report",
                "context": {"urgency_level": 0.6},
                "urgency_level": 0.6
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/adhd/executive/task-breakdown",
                    json=request_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'task_breakdown' in data
                breakdown = data['task_breakdown']
                assert breakdown['original_task'] == "Write project report"
                assert len(breakdown['subtasks']) == 3
                assert breakdown['estimated_total_time'] == 105
                assert breakdown['complexity_level'] == 'medium'
    
    @pytest.mark.asyncio
    async def test_procrastination_assessment_endpoint(self, auth_headers):
        """Test procrastination assessment endpoint."""
        with patch('adhd.executive_function.procrastination_intervenor') as mock_intervenor:
            mock_intervenor.assess_procrastination_risk.return_value = (
                0.7,  # risk score
                [Mock(value='overwhelm'), Mock(value='perfectionism')]  # triggers
            )
            
            mock_intervenor.provide_intervention.return_value = {
                'level': 3,
                'strategies': ['Break into smaller steps', 'Set timer for 5 minutes'],
                'immediate_actions': ['Just start with anything'],
                'mindset_shifts': ['Progress over perfection']
            }
            
            request_data = {
                "task_description": "Write important presentation",
                "context": {"deadline_pressure": True}
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/adhd/executive/procrastination-assessment",
                    json=request_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'procrastination_assessment' in data
                assessment = data['procrastination_assessment']
                assert assessment['risk_score'] == 0.7
                assert len(assessment['triggers']) == 2
                assert assessment['intervention']['level'] == 3
    
    @pytest.mark.asyncio
    async def test_working_memory_endpoints(self, auth_headers):
        """Test working memory store and retrieve endpoints."""
        with patch('adhd.executive_function.working_memory_support') as mock_support:
            # Test store
            mock_support.store_information.return_value = "aid_123"
            
            store_request = {
                "action": "store",
                "information_type": "task_requirement",
                "content": "Must include budget analysis section",
                "priority": 4,
                "expires_hours": 24
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/adhd/executive/working-memory",
                    json=store_request,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data['action'] == 'store'
                assert data['aid_id'] == 'aid_123'
                assert data['success'] is True
            
            # Test retrieve
            mock_aid = Mock()
            mock_aid.information_type = 'task_requirement'
            mock_aid.content = 'Must include budget analysis section'
            mock_aid.priority = 4
            mock_aid.retrieval_cues = ['budget', 'analysis']
            
            mock_support.retrieve_information.return_value = [mock_aid]
            
            retrieve_request = {
                "action": "retrieve",
                "query": "budget requirements"
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/adhd/executive/working-memory",
                    json=retrieve_request,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert data['action'] == 'retrieve'
                assert data['count'] == 1
                assert len(data['aids']) == 1
                assert data['aids'][0]['information_type'] == 'task_requirement'
    
    @pytest.mark.asyncio
    async def test_ml_insights_endpoint(self, auth_headers):
        """Test ML insights endpoint."""
        with patch('adhd.ml_pipeline.ml_pipeline') as mock_pipeline:
            mock_pipeline.get_model_performance.return_value = {
                'user_id': 'test_adhd_user',
                'models_trained': ['pattern_classifier', 'crisis_detector'],
                'metrics': {
                    'pattern_classifier': {
                        'accuracy': 0.85,
                        'training_samples': 45
                    }
                },
                'recent_performance': [
                    {'timestamp': datetime.utcnow().isoformat(), 'accuracy': 0.87}
                ]
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/adhd/ml/insights",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'ml_insights' in data
                insights = data['ml_insights']
                assert len(insights['models_trained']) == 2
                assert 'pattern_classifier' in insights['metrics']
                assert insights['metrics']['pattern_classifier']['accuracy'] == 0.85
    
    @pytest.mark.asyncio
    async def test_adaptation_summary_endpoint(self, auth_headers):
        """Test adaptation summary endpoint."""
        with patch('adhd.adaptation_engine.adaptation_engine') as mock_engine:
            mock_engine.get_adaptation_summary.return_value = {
                'total_adaptations': 15,
                'recent_adaptations': 3,
                'average_effectiveness': 0.78,
                'adaptation_types': ['cognitive_load_reduction', 'interface_simplification'],
                'most_effective_adaptation': 'cognitive_load_reduction'
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/adhd/system/adaptation-summary",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                
                assert 'adaptation_summary' in data
                summary = data['adaptation_summary']
                assert summary['total_adaptations'] == 15
                assert summary['average_effectiveness'] == 0.78
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test ADHD features health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/adhd/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['status'] == 'healthy'
            assert data['enhanced_features_available'] is True
            assert 'components' in data
            assert 'pattern_engine' in data['components']
            assert 'user_profiling' in data['components']
    
    @pytest.mark.asyncio
    async def test_authentication_required(self):
        """Test that endpoints require authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test without auth headers
            response = await client.post(
                "/adhd/chat/enhanced",
                json={"message": "test"}
            )
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_validation_errors(self, auth_headers):
        """Test request validation errors."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test enhanced chat with invalid data
            response = await client.post(
                "/adhd/chat/enhanced",
                json={"message": ""},  # Empty message
                headers=auth_headers
            )
            
            assert response.status_code == 422  # Validation error
            
            # Test task breakdown without required fields
            response = await client.post(
                "/adhd/executive/task-breakdown",
                json={},  # Missing task_description
                headers=auth_headers
            )
            
            assert response.status_code == 422