"""
Unit tests for Enhanced User Profiling System.

Tests the user profile management, personalization adaptation,
and preference management functionality.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from adhd.user_profile import (
    UserProfileManager, ADHDUserProfile, EnergyPattern, 
    CognitiveLoadPreference, InteractionStyle, ADHDSubtype,
    EnergySchedule, CognitiveThresholds, NudgePreferences
)


class TestADHDUserProfile:
    """Test suite for ADHD User Profile model."""
    
    def test_profile_creation_defaults(self):
        """Test profile creation with default values."""
        profile = ADHDUserProfile(user_id="test_user")
        
        assert profile.user_id == "test_user"
        assert profile.adhd_subtype == ADHDSubtype.UNSPECIFIED
        assert profile.subtype_confidence == 0.0
        assert profile.energy_pattern == EnergyPattern.UNPREDICTABLE
        assert profile.cognitive_load_preference == CognitiveLoadPreference.ADAPTIVE
        assert profile.interaction_style == InteractionStyle.ENCOURAGING
        assert profile.hyperfocus_tendency == 0.3
        assert profile.learning_enabled is True
        assert profile.adaptation_enabled is True
    
    def test_profile_serialization(self):
        """Test profile serialization to dict."""
        profile = ADHDUserProfile(
            user_id="test_user",
            adhd_subtype=ADHDSubtype.COMBINED_PRESENTATION,
            subtype_confidence=0.8,
            energy_pattern=EnergyPattern.MORNING_PEAK,
            hyperfocus_tendency=0.7
        )
        
        data = profile.dict()
        
        assert data['user_id'] == "test_user"
        assert data['adhd_subtype'] == "combined"
        assert data['subtype_confidence'] == 0.8
        assert data['energy_pattern'] == "morning_peak"
        assert data['hyperfocus_tendency'] == 0.7
    
    def test_profile_with_custom_thresholds(self):
        """Test profile with custom cognitive thresholds."""
        thresholds = CognitiveThresholds(
            overwhelm_threshold=0.75,
            optimal_load=0.55,
            minimum_engagement=0.25,
            context_item_limit=6,
            response_length_preference=120,
            complexity_tolerance=0.65
        )
        
        profile = ADHDUserProfile(
            user_id="test_user",
            cognitive_thresholds=thresholds
        )
        
        assert profile.cognitive_thresholds.overwhelm_threshold == 0.75
        assert profile.cognitive_thresholds.context_item_limit == 6
        assert profile.cognitive_thresholds.response_length_preference == 120
    
    def test_profile_with_energy_schedule(self):
        """Test profile with energy schedule."""
        schedule = EnergySchedule(
            peak_hours=[9, 10, 11, 14, 15],
            low_hours=[13, 16, 17],
            variable_hours=[12, 18],
            pattern_confidence=0.7,
            last_updated=datetime.utcnow()
        )
        
        profile = ADHDUserProfile(
            user_id="test_user",
            energy_schedule=schedule,
            energy_pattern=EnergyPattern.MORNING_PEAK
        )
        
        assert profile.energy_schedule.peak_hours == [9, 10, 11, 14, 15]
        assert profile.energy_schedule.pattern_confidence == 0.7
        assert profile.energy_pattern == EnergyPattern.MORNING_PEAK
    
    def test_profile_with_nudge_preferences(self):
        """Test profile with nudge preferences."""
        nudge_prefs = NudgePreferences(
            preferred_methods=['web', 'telegram'],
            timing_preferences={'morning': '09:00', 'evening': '18:00'},
            frequency_limits={'hourly': 2, 'daily': 8},
            urgency_escalation=True,
            quiet_hours=[(22, 7)],
            effectiveness_scores={'web': 0.8, 'telegram': 0.6}
        )
        
        profile = ADHDUserProfile(
            user_id="test_user",
            nudge_preferences=nudge_prefs
        )
        
        assert profile.nudge_preferences.preferred_methods == ['web', 'telegram']
        assert profile.nudge_preferences.effectiveness_scores['web'] == 0.8
        assert profile.nudge_preferences.quiet_hours == [(22, 7)]


class TestUserProfileManager:
    """Test suite for User Profile Manager."""
    
    @pytest.fixture
    def profile_manager(self):
        """Create profile manager for testing."""
        return UserProfileManager()
    
    @pytest.fixture
    def mock_trace_memory(self):
        """Mock trace memory."""
        with patch('adhd.user_profile.trace_memory') as mock:
            mock.get_user_traces.return_value = asyncio.coroutine(lambda: [])()
            mock.store_trace.return_value = asyncio.coroutine(lambda: None)()
            yield mock
    
    @pytest.mark.asyncio
    async def test_create_initial_profile(self, profile_manager, mock_trace_memory):
        """Test creation of initial user profile."""
        profile = await profile_manager._create_initial_profile("test_user")
        
        assert profile.user_id == "test_user"
        assert profile.cognitive_thresholds is not None
        assert profile.nudge_preferences is not None
        assert profile.cognitive_thresholds.overwhelm_threshold == 0.7
        assert profile.nudge_preferences.preferred_methods == ['web']
    
    @pytest.mark.asyncio
    async def test_get_or_create_profile_new_user(self, profile_manager, mock_trace_memory):
        """Test getting profile for new user."""
        with patch.object(profile_manager, '_load_profile_from_traces', return_value=asyncio.coroutine(lambda: None)()):
            profile = await profile_manager.get_or_create_profile("new_user")
            
            assert profile.user_id == "new_user"
            assert "new_user" in profile_manager._profiles
    
    @pytest.mark.asyncio
    async def test_get_or_create_profile_existing_user(self, profile_manager, mock_trace_memory):
        """Test getting profile for existing user."""
        # First call creates the profile
        profile1 = await profile_manager.get_or_create_profile("existing_user")
        
        # Second call should return the same profile
        profile2 = await profile_manager.get_or_create_profile("existing_user")
        
        assert profile1 is profile2
        assert profile1.user_id == "existing_user"
    
    @pytest.mark.asyncio
    async def test_update_profile_from_interaction(self, profile_manager, mock_trace_memory):
        """Test updating profile based on interaction data."""
        profile = await profile_manager.get_or_create_profile("test_user")
        initial_version = profile.profile_version
        
        interaction_data = {
            'patterns_detected': [
                {'type': 'hyperfocus', 'confidence': 0.8}
            ],
            'energy_indicators': ['high_energy'],
            'cognitive_load_indicators': ['low_load'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await profile_manager.update_profile_from_interaction("test_user", interaction_data)
        
        updated_profile = await profile_manager.get_or_create_profile("test_user")
        assert updated_profile.profile_version > initial_version
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, profile_manager, mock_trace_memory):
        """Test updating user preferences."""
        await profile_manager.get_or_create_profile("test_user")
        
        preferences = {
            'cognitive_load_preference': 'minimal',
            'interaction_style': 'direct',
            'interface_complexity': 'simple',
            'nudge_methods': ['telegram', 'email'],
            'privacy_settings': {
                'learning_enabled': False,
                'data_sharing_consent': True
            }
        }
        
        success = await profile_manager.update_user_preferences("test_user", preferences)
        
        assert success
        updated_profile = await profile_manager.get_or_create_profile("test_user")
        assert updated_profile.cognitive_load_preference == CognitiveLoadPreference.MINIMAL
        assert updated_profile.interaction_style == InteractionStyle.DIRECT
        assert updated_profile.interface_complexity == 'simple'
        assert updated_profile.learning_enabled is False
    
    @pytest.mark.asyncio
    async def test_get_personalized_settings(self, profile_manager, mock_trace_memory):
        """Test getting personalized settings."""
        # Create profile with custom settings
        profile = await profile_manager.get_or_create_profile("test_user")
        profile.cognitive_thresholds.context_item_limit = 6
        profile.cognitive_thresholds.response_length_preference = 120
        profile.interface_complexity = 'moderate'
        
        settings = await profile_manager.get_personalized_settings("test_user")
        
        assert settings['cognitive_load']['max_context_items'] == 6
        assert settings['cognitive_load']['response_length'] == 120
        assert settings['interface']['complexity'] == 'moderate'
        assert 'nudging' in settings
        assert 'patterns' in settings
    
    @pytest.mark.asyncio
    async def test_energy_pattern_updates(self, profile_manager, mock_trace_memory):
        """Test updating energy patterns from interactions."""
        profile = await profile_manager.get_or_create_profile("test_user")
        
        # Simulate morning high energy interaction
        insights = {
            'timestamp': datetime.utcnow().replace(hour=9),
            'energy_indicators': ['high_energy']
        }
        
        await profile_manager._update_energy_patterns(profile, insights)
        
        assert profile.energy_schedule is not None
        assert 9 in profile.energy_schedule.peak_hours
        assert profile.energy_schedule.pattern_confidence > 0
    
    @pytest.mark.asyncio
    async def test_cognitive_thresholds_adaptation(self, profile_manager, mock_trace_memory):
        """Test adaptive adjustment of cognitive thresholds."""
        profile = await profile_manager.get_or_create_profile("test_user")
        original_threshold = profile.cognitive_thresholds.overwhelm_threshold
        
        # Simulate high load indication
        insights = {
            'cognitive_load_indicators': ['high_load', 'slow_processing'],
            'preference_indicators': ['prefers_simple']
        }
        
        await profile_manager._update_cognitive_thresholds(profile, insights)
        
        # Threshold should be lowered due to high load indication
        assert profile.cognitive_thresholds.overwhelm_threshold < original_threshold
        assert profile.cognitive_thresholds.response_length_preference < 150
    
    @pytest.mark.asyncio
    async def test_nudge_effectiveness_tracking(self, profile_manager, mock_trace_memory):
        """Test tracking nudge effectiveness."""
        profile = await profile_manager.get_or_create_profile("test_user")
        
        insights = {
            'effectiveness_data': {
                'web': 0.8,
                'telegram': 0.6
            }
        }
        
        await profile_manager._update_nudge_effectiveness(profile, insights)
        
        assert profile.nudge_preferences.effectiveness_scores['web'] > 0.5
        assert profile.nudge_preferences.effectiveness_scores['telegram'] > 0.5
    
    @pytest.mark.asyncio
    async def test_profile_persistence(self, profile_manager, mock_trace_memory):
        """Test profile persistence to trace memory."""
        profile = await profile_manager.get_or_create_profile("test_user")
        
        await profile_manager._save_profile(profile)
        
        # Check that store_trace was called
        mock_trace_memory.store_trace.assert_called()
        call_args = mock_trace_memory.store_trace.call_args[0]
        trace_record = call_args[0]
        
        assert trace_record.event_type == "profile_update"
        assert trace_record.user_id == "test_user"
        assert 'user_id' in trace_record.event_data
    
    @pytest.mark.asyncio
    async def test_pattern_based_adaptation(self, profile_manager, mock_trace_memory):
        """Test adaptation based on detected patterns."""
        profile = await profile_manager.get_or_create_profile("test_user")
        original_hyperfocus = profile.hyperfocus_tendency
        
        # Mock pattern objects
        mock_patterns = [
            Mock(
                pattern_type=Mock(value='hyperfocus'),
                severity=Mock(value='high'),
                confidence=0.8
            ),
            Mock(
                pattern_type=Mock(value='overwhelm'),
                severity=Mock(value='critical'),
                confidence=0.9
            )
        ]
        
        await profile_manager.adapt_to_pattern_detection("test_user", mock_patterns)
        
        updated_profile = await profile_manager.get_or_create_profile("test_user")
        # Hyperfocus tendency should increase due to detected pattern
        assert updated_profile.hyperfocus_tendency >= original_hyperfocus
    
    def test_default_settings_fallback(self, profile_manager):
        """Test fallback to default settings."""
        default_settings = profile_manager._get_default_settings()
        
        assert 'cognitive_load' in default_settings
        assert 'nudging' in default_settings
        assert 'interface' in default_settings
        assert 'patterns' in default_settings
        
        assert default_settings['cognitive_load']['max_context_items'] == 8
        assert default_settings['interface']['complexity'] == 'adaptive'
        assert default_settings['patterns']['adhd_subtype'] == 'unspecified'


class TestEnergySchedule:
    """Test energy schedule functionality."""
    
    def test_energy_schedule_creation(self):
        """Test creating energy schedule."""
        schedule = EnergySchedule(
            peak_hours=[9, 10, 14, 15],
            low_hours=[13, 16, 17],
            variable_hours=[11, 12],
            pattern_confidence=0.8,
            last_updated=datetime.utcnow()
        )
        
        assert len(schedule.peak_hours) == 4
        assert 9 in schedule.peak_hours
        assert 13 in schedule.low_hours
        assert schedule.pattern_confidence == 0.8
    
    def test_energy_schedule_validation(self):
        """Test energy schedule with invalid hours."""
        # Should handle hours outside 0-23 range gracefully
        schedule = EnergySchedule(
            peak_hours=[9, 25],  # Invalid hour
            low_hours=[13],
            variable_hours=[],
            pattern_confidence=0.5,
            last_updated=datetime.utcnow()
        )
        
        # The model should still be created (validation handled elsewhere)
        assert 9 in schedule.peak_hours
        assert 25 in schedule.peak_hours  # Model doesn't validate range


class TestCognitiveThresholds:
    """Test cognitive thresholds functionality."""
    
    def test_cognitive_thresholds_creation(self):
        """Test creating cognitive thresholds."""
        thresholds = CognitiveThresholds(
            overwhelm_threshold=0.8,
            optimal_load=0.6,
            minimum_engagement=0.3,
            context_item_limit=10,
            response_length_preference=200,
            complexity_tolerance=0.7
        )
        
        assert thresholds.overwhelm_threshold == 0.8
        assert thresholds.optimal_load == 0.6
        assert thresholds.context_item_limit == 10
        assert thresholds.response_length_preference == 200
    
    def test_cognitive_thresholds_defaults(self):
        """Test cognitive thresholds with some defaults."""
        thresholds = CognitiveThresholds(
            overwhelm_threshold=0.75,
            optimal_load=0.5,
            minimum_engagement=0.25,
            context_item_limit=8,
            response_length_preference=150,
            complexity_tolerance=0.6
        )
        
        # All values should be within reasonable ranges
        assert 0.0 <= thresholds.overwhelm_threshold <= 1.0
        assert 0.0 <= thresholds.optimal_load <= 1.0
        assert thresholds.context_item_limit > 0
        assert thresholds.response_length_preference > 0


class TestNudgePreferences:
    """Test nudge preferences functionality."""
    
    def test_nudge_preferences_creation(self):
        """Test creating nudge preferences."""
        prefs = NudgePreferences(
            preferred_methods=['web', 'telegram', 'email'],
            timing_preferences={'morning': '09:00', 'evening': '17:00'},
            frequency_limits={'hourly': 3, 'daily': 10},
            urgency_escalation=True,
            quiet_hours=[(22, 7), (12, 13)],
            effectiveness_scores={'web': 0.8, 'telegram': 0.7}
        )
        
        assert 'web' in prefs.preferred_methods
        assert prefs.timing_preferences['morning'] == '09:00'
        assert prefs.frequency_limits['daily'] == 10
        assert prefs.urgency_escalation is True
        assert len(prefs.quiet_hours) == 2
        assert prefs.effectiveness_scores['web'] == 0.8
    
    def test_empty_nudge_preferences(self):
        """Test nudge preferences with minimal data."""
        prefs = NudgePreferences(
            preferred_methods=[],
            timing_preferences={},
            frequency_limits={},
            urgency_escalation=False,
            quiet_hours=[],
            effectiveness_scores={}
        )
        
        assert len(prefs.preferred_methods) == 0
        assert len(prefs.timing_preferences) == 0
        assert prefs.urgency_escalation is False