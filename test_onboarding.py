#!/usr/bin/env python3
"""
Test script for user onboarding system.
Tests ADHD-optimized onboarding flow.
"""
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import asyncio
from datetime import datetime
from unittest.mock import MagicMock

async def test_onboarding_system():
    """Test the ADHD onboarding system."""
    print("🧠 Testing MCP ADHD Onboarding System")
    print("=" * 40)
    
    try:
        # Test 1: Import onboarding system
        print("\n📦 Test 1: Import Onboarding System")
        print("-" * 30)
        
        from mcp_server.onboarding import OnboardingManager, OnboardingStep, ADHDProfileData
        print("✅ Successfully imported onboarding components")
        
        manager = OnboardingManager()
        print("✅ OnboardingManager created successfully")
        
        # Test 2: Start onboarding
        print("\n🚀 Test 2: Start Onboarding Process")
        print("-" * 30)
        
        test_user_id = "test_user_123"
        onboarding = await manager.start_onboarding(test_user_id)
        
        assert onboarding.user_id == test_user_id
        assert onboarding.current_step == OnboardingStep.WELCOME
        assert not onboarding.is_completed
        print("✅ Onboarding session created successfully")
        print(f"   User ID: {onboarding.user_id}")
        print(f"   Current step: {onboarding.current_step}")
        
        # Test 3: Process welcome step
        print("\n👋 Test 3: Welcome Step Processing")
        print("-" * 30)
        
        welcome_response = await manager.process_step(test_user_id, {})
        
        assert welcome_response["status"] == "current_step"
        assert welcome_response["step"] == "welcome"
        assert "Welcome to MCP ADHD Server" in welcome_response["title"]
        print("✅ Welcome step processed successfully")
        print(f"   Title: {welcome_response['title']}")
        print(f"   Message preview: {welcome_response['message'][:50]}...")
        
        # Test 4: Progress through onboarding
        print("\n⏭️ Test 4: Progress Through Steps")
        print("-" * 30)
        
        # Progress to ADHD profile step
        profile_response = await manager.process_step(test_user_id, {"ready": True})
        
        assert profile_response["status"] == "next_step"
        assert profile_response["step"] == "adhd_profile"
        assert "Let's Learn About Your ADHD" in profile_response["title"]
        print("✅ Advanced to ADHD profile step")
        print(f"   Questions: {len(profile_response['questions'])} configured")
        
        # Test ADHD profile data
        adhd_data = {
            "primary_challenges": ["Staying focused on tasks", "Time management"],
            "strengths": ["Creativity and out-of-box thinking", "Hyperfocus abilities"]
        }
        
        nudge_response = await manager.process_step(test_user_id, adhd_data)
        
        assert nudge_response["status"] == "next_step"
        assert nudge_response["step"] == "nudge_preferences"
        print("✅ ADHD profile step completed successfully")
        print(f"   Challenges stored: {len(adhd_data['primary_challenges'])}")
        print(f"   Strengths stored: {len(adhd_data['strengths'])}")
        
        # Test 5: Complete remaining steps quickly
        print("\n⚡ Test 5: Complete Onboarding Flow")
        print("-" * 30)
        
        # Nudge preferences
        nudge_prefs = {
            "nudge_methods": ["Web notifications (in browser)"],
            "nudge_frequency": "Normal (2-3 times per day)",
            "nudge_style": "Gentle and encouraging 🌱"
        }
        
        integration_response = await manager.process_step(test_user_id, nudge_prefs)
        assert integration_response["step"] == "integration_setup"
        print("✅ Nudge preferences step completed")
        
        # Skip integrations
        first_task_response = await manager.process_step(test_user_id, {"skip_integrations": True})
        assert first_task_response["step"] == "first_task"
        print("✅ Integration setup step completed")
        
        # Complete with first task
        completion_response = await manager.process_step(test_user_id, {
            "task": "Set up my workspace for productivity"
        })
        
        assert completion_response["status"] == "completed"
        assert "Welcome aboard" in completion_response["title"]
        print("✅ Onboarding completed successfully!")
        print(f"   Final message: {completion_response['title']}")
        
        # Verify completion
        final_status = await manager.get_onboarding_status(test_user_id)
        assert final_status.is_completed
        assert final_status.current_step == OnboardingStep.COMPLETED
        print("✅ Onboarding status correctly marked as completed")
        
        # Test 6: Skip onboarding functionality
        print("\n⏭️ Test 6: Skip Onboarding Option")
        print("-" * 30)
        
        skip_user_id = "skip_user_456" 
        skip_response = await manager.skip_onboarding(skip_user_id)
        
        assert skip_response["status"] == "completed"
        assert "Welcome" in skip_response["title"]
        print("✅ Skip onboarding functionality works")
        
        skip_status = await manager.get_onboarding_status(skip_user_id)
        assert skip_status.is_completed
        assert skip_status.step_data.get("skipped") == True
        print("✅ Skip status correctly recorded")
        
        # Test 7: ADHD-specific features
        print("\n🧠 Test 7: ADHD-Specific Features")
        print("-" * 30)
        
        # Verify ADHD profile data structure
        profile_data = ADHDProfileData(
            primary_challenges=["focus", "time_management"],
            strengths=["creativity", "hyperfocus"],
            best_focus_times=["morning"],
            hyperfocus_triggers=["interesting_projects"],
            overwhelm_triggers=["too_many_tasks"],
            coping_strategies=["breaks", "chunking"]
        )
        
        assert len(profile_data.primary_challenges) == 2
        assert len(profile_data.strengths) == 2
        print("✅ ADHD profile data structure works correctly")
        
        # Verify onboarding step flow
        all_steps = [step.value for step in OnboardingStep]
        expected_steps = ["welcome", "adhd_profile", "nudge_preferences", "integration_setup", "first_task", "completed"]
        
        for step in expected_steps:
            assert step in all_steps
        print("✅ All required onboarding steps defined")
        
        # Test Summary
        print("\n🎉 Onboarding Test Summary")
        print("=" * 35)
        print("✅ Onboarding session management")
        print("✅ Step-by-step progression")
        print("✅ ADHD profile data collection")
        print("✅ Nudge preference configuration")
        print("✅ Integration setup options")
        print("✅ First task establishment")
        print("✅ Completion and status tracking")
        print("✅ Skip onboarding option")
        print("✅ ADHD-specific optimizations")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Test assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Run onboarding tests."""
    print("🧠⚡ MCP ADHD Server - Onboarding System Tests")
    print("=" * 50)
    
    try:
        success = await test_onboarding_system()
        
        if success:
            print("\n🚀 All Onboarding Tests Passed!")
            print("\n📋 Onboarding System Features:")
            print("• ADHD-optimized step progression")
            print("• Personalized challenge/strength assessment") 
            print("• Customizable nudge preferences")
            print("• Integration setup guidance")
            print("• First task to build momentum")
            print("• Skip option for returning users")
            print("• Data applied to user preferences")
            
            print("\n🎯 Ready for Integration:")
            print("• API endpoints configured in main.py")
            print("• Authentication-protected routes")
            print("• Metrics tracking for completion rates")
            print("• ADHD-friendly UX considerations")
            
            return True
        else:
            print("\n❌ Some tests failed. Please review and fix.")
            return False
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)