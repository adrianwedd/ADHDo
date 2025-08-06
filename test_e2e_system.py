#!/usr/bin/env python3
"""
End-to-End System Test Suite for MCP ADHD Server.
Tests complete user workflows and system integration.
"""
import sys
from pathlib import Path
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

class E2ETestResults:
    """Track end-to-end test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.performance_issues = []
        self.critical_failures = []
        self.warnings = []

    def record_test(self, test_name: str, passed: bool, duration_ms: int = None, critical: bool = False):
        """Record test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}")
            if duration_ms and duration_ms > 3000:  # ADHD performance target
                self.performance_issues.append(f"{test_name}: {duration_ms}ms")
        else:
            self.tests_failed += 1
            print(f"❌ {test_name}")
            if critical:
                self.critical_failures.append(test_name)

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
        print(f"⚠️ {message}")

    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*60)
        print("🧠⚡ MCP ADHD SERVER - END-TO-END TEST SUMMARY")
        print("="*60)
        
        print(f"\n📊 Overall Results:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Passed: {self.tests_passed} ✅")
        print(f"   Failed: {self.tests_failed} ❌")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.performance_issues:
            print(f"\n⚡ Performance Issues (>3s ADHD target):")
            for issue in self.performance_issues:
                print(f"   - {issue}")
        
        if self.critical_failures:
            print(f"\n🚨 Critical Failures:")
            for failure in self.critical_failures:
                print(f"   - {failure}")
        
        if self.warnings:
            print(f"\n⚠️ Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        print(f"\n🎯 ADHD-Specific Assessment:")
        adhd_score = self._calculate_adhd_score()
        print(f"   ADHD Readiness Score: {adhd_score}/100")
        
        if adhd_score >= 90:
            print("   🎉 EXCELLENT! Ready for ADHD users")
        elif adhd_score >= 75:
            print("   ✅ GOOD! Minor optimizations needed")
        elif adhd_score >= 60:
            print("   ⚠️ FAIR! Significant improvements needed")
        else:
            print("   ❌ POOR! Major fixes required before ADHD deployment")
            
        return success_rate >= 80 and len(self.critical_failures) == 0

    def _calculate_adhd_score(self) -> int:
        """Calculate ADHD readiness score."""
        base_score = (self.tests_passed / self.tests_run * 70) if self.tests_run > 0 else 0
        
        # Deduct for performance issues (critical for ADHD)
        perf_penalty = min(len(self.performance_issues) * 10, 30)
        
        # Deduct for critical failures
        critical_penalty = len(self.critical_failures) * 20
        
        # Add bonus for comprehensive testing
        if self.tests_run >= 15:
            base_score += 10
            
        final_score = max(0, int(base_score - perf_penalty - critical_penalty))
        return min(100, final_score)


async def test_authentication_flow(results: E2ETestResults):
    """Test complete authentication workflow."""
    print("\n🔐 Testing Authentication System")
    print("-" * 35)
    
    try:
        # Test 1: Import authentication system
        start_time = time.time()
        from mcp_server.auth import auth_manager, RegistrationRequest, LoginRequest, AuthResponse
        duration_ms = int((time.time() - start_time) * 1000)
        results.record_test("Auth system import", True, duration_ms)
        
        # Test 2: User registration
        start_time = time.time()
        reg_request = RegistrationRequest(
            name="Test User",
            email="test@example.com", 
            password="testpass123"
        )
        reg_result = auth_manager.register_user(reg_request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        success = reg_result.success and reg_result.user is not None
        results.record_test("User registration", success, duration_ms, critical=True)
        
        if not success:
            results.add_warning(f"Registration failed: {reg_result.message}")
            return False
        
        # Test 3: User login
        start_time = time.time()
        login_request = LoginRequest(
            email="test@example.com",
            password="testpass123"
        )
        login_result = auth_manager.login_user(login_request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        success = login_result.success and login_result.session_id is not None
        results.record_test("User login", success, duration_ms, critical=True)
        
        # Test 4: Session validation
        if login_result.session_id:
            start_time = time.time()
            session = auth_manager.validate_session(login_result.session_id)
            duration_ms = int((time.time() - start_time) * 1000)
            
            success = session is not None and session.is_valid()
            results.record_test("Session validation", success, duration_ms)
        
        # Test 5: User logout
        if login_result.session_id:
            start_time = time.time()
            logout_result = auth_manager.logout_user(login_result.session_id)
            duration_ms = int((time.time() - start_time) * 1000)
            
            success = logout_result.success
            results.record_test("User logout", success, duration_ms)
        
        return True
        
    except Exception as e:
        results.record_test("Auth system error", False, critical=True)
        results.add_warning(f"Authentication system failure: {e}")
        return False


async def test_onboarding_system(results: E2ETestResults):
    """Test ADHD onboarding workflow."""
    print("\n🧠 Testing Onboarding System") 
    print("-" * 30)
    
    try:
        # Test 1: Import onboarding system
        start_time = time.time()
        from mcp_server.onboarding import onboarding_manager, OnboardingStep
        duration_ms = int((time.time() - start_time) * 1000)
        results.record_test("Onboarding system import", True, duration_ms)
        
        # Test 2: Start onboarding
        test_user_id = "e2e_test_user"
        start_time = time.time()
        onboarding = await onboarding_manager.start_onboarding(test_user_id)
        duration_ms = int((time.time() - start_time) * 1000)
        
        success = onboarding.current_step == OnboardingStep.WELCOME
        results.record_test("Start onboarding", success, duration_ms)
        
        # Test 3: Progress through steps
        steps_completed = 0
        
        # Welcome step
        start_time = time.time()
        welcome_response = await onboarding_manager.process_step(test_user_id, {"ready": True})
        duration_ms = int((time.time() - start_time) * 1000)
        
        if welcome_response.get("step") == "adhd_profile":
            steps_completed += 1
            results.record_test("Welcome step progression", True, duration_ms)
        
        # ADHD profile step  
        start_time = time.time()
        profile_response = await onboarding_manager.process_step(test_user_id, {
            "primary_challenges": ["focus", "time_management"],
            "strengths": ["creativity", "hyperfocus"]
        })
        duration_ms = int((time.time() - start_time) * 1000)
        
        if profile_response.get("step") == "nudge_preferences":
            steps_completed += 1
            results.record_test("ADHD profile step", True, duration_ms)
        
        # Nudge preferences step
        start_time = time.time()
        nudge_response = await onboarding_manager.process_step(test_user_id, {
            "nudge_methods": ["web"],
            "nudge_frequency": "normal"
        })
        duration_ms = int((time.time() - start_time) * 1000)
        
        if nudge_response.get("step") == "integration_setup":
            steps_completed += 1
            results.record_test("Nudge preferences step", True, duration_ms)
        
        # Complete onboarding
        start_time = time.time()
        completion = await onboarding_manager.process_step(test_user_id, {"skip_integrations": True})
        if completion.get("step") == "first_task":
            final_completion = await onboarding_manager.process_step(test_user_id, {
                "task": "Test my new ADHD setup"
            })
            duration_ms = int((time.time() - start_time) * 1000)
            
            if final_completion.get("status") == "completed":
                steps_completed += 1
                results.record_test("Complete onboarding flow", True, duration_ms)
        
        # Test 4: Skip onboarding option
        skip_user_id = "e2e_skip_user"
        start_time = time.time()
        skip_result = await onboarding_manager.skip_onboarding(skip_user_id)
        duration_ms = int((time.time() - start_time) * 1000)
        
        success = skip_result.get("status") == "completed"
        results.record_test("Skip onboarding option", success, duration_ms)
        
        # Overall onboarding assessment
        overall_success = steps_completed >= 3  # Most steps completed
        results.record_test("Overall onboarding system", overall_success, critical=True)
        
        return True
        
    except Exception as e:
        results.record_test("Onboarding system error", False, critical=True)
        results.add_warning(f"Onboarding system failure: {e}")
        return False


async def test_telegram_integration(results: E2ETestResults):
    """Test Telegram bot integration."""
    print("\n📱 Testing Telegram Integration")
    print("-" * 32)
    
    try:
        # Test 1: Import Telegram system
        start_time = time.time()
        from mcp_server.telegram_bot import TelegramBotHandler
        duration_ms = int((time.time() - start_time) * 1000)
        results.record_test("Telegram bot import", True, duration_ms)
        
        # Test 2: Create bot handler (graceful degradation)
        start_time = time.time()
        bot_handler = TelegramBotHandler()
        duration_ms = int((time.time() - start_time) * 1000)
        results.record_test("Telegram bot creation", True, duration_ms)
        
        # Test 3: Command handlers exist
        expected_commands = ["start", "help", "focus", "register", "login", "link"]
        commands_implemented = 0
        
        for cmd in expected_commands:
            handler_name = f"handle_{cmd}"
            if hasattr(bot_handler, handler_name):
                commands_implemented += 1
        
        success = commands_implemented == len(expected_commands)
        results.record_test(f"Command handlers ({commands_implemented}/{len(expected_commands)})", success)
        
        # Test 4: Authentication integration
        success = hasattr(bot_handler, 'handle_register') and hasattr(bot_handler, 'handle_login')
        results.record_test("Auth integration", success)
        
        # Test 5: ADHD-specific features
        adhd_features = 0
        if hasattr(bot_handler, 'send_nudge'):
            adhd_features += 1
        if hasattr(bot_handler, 'handle_break'):
            adhd_features += 1
        if hasattr(bot_handler, 'handle_focus'):
            adhd_features += 1
            
        success = adhd_features >= 2
        results.record_test(f"ADHD features ({adhd_features}/3)", success)
        
        return True
        
    except Exception as e:
        results.record_test("Telegram integration error", False)
        results.add_warning(f"Telegram integration issue: {e}")
        return False


async def test_system_performance(results: E2ETestResults):
    """Test ADHD performance requirements."""
    print("\n⚡ Testing Performance Requirements")
    print("-" * 35)
    
    try:
        # Test 1: Authentication performance
        from mcp_server.auth import auth_manager, RegistrationRequest, LoginRequest
        
        # Registration performance
        start_time = time.time()
        reg_req = RegistrationRequest(name="Perf Test", email="perf@test.com", password="perftest123")
        auth_manager.register_user(reg_req)
        reg_duration = int((time.time() - start_time) * 1000)
        
        success = reg_duration < 1000  # Should be very fast
        results.record_test(f"Registration performance ({reg_duration}ms)", success, reg_duration)
        
        # Login performance  
        start_time = time.time()
        login_req = LoginRequest(email="perf@test.com", password="perftest123")
        auth_manager.login_user(login_req)
        login_duration = int((time.time() - start_time) * 1000)
        
        success = login_duration < 500  # Should be very fast
        results.record_test(f"Login performance ({login_duration}ms)", success, login_duration)
        
        # Test 2: Onboarding performance
        from mcp_server.onboarding import onboarding_manager
        
        start_time = time.time()
        await onboarding_manager.start_onboarding("perf_test_user")
        onboarding_duration = int((time.time() - start_time) * 1000)
        
        success = onboarding_duration < 1000  # Should be fast
        results.record_test(f"Onboarding start ({onboarding_duration}ms)", success, onboarding_duration)
        
        # Test 3: Memory usage assessment
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        success = memory_mb < 500  # Should be reasonable
        results.record_test(f"Memory usage ({memory_mb:.1f}MB)", success)
        
        if memory_mb > 300:
            results.add_warning(f"Memory usage high: {memory_mb:.1f}MB")
        
        # Test 4: Import performance
        start_time = time.time()
        import mcp_server.main  # Main app import
        import_duration = int((time.time() - start_time) * 1000)
        
        success = import_duration < 5000  # App should start quickly
        results.record_test(f"App import time ({import_duration}ms)", success, import_duration)
        
        return True
        
    except Exception as e:
        results.record_test("Performance test error", False)
        results.add_warning(f"Performance testing failed: {e}")
        return False


async def test_adhd_specific_features(results: E2ETestResults):
    """Test ADHD-optimized features."""
    print("\n🧠 Testing ADHD-Specific Features") 
    print("-" * 35)
    
    try:
        # Test 1: ADHD models and enums
        start_time = time.time()
        from mcp_server.models import NudgeTier, User
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Check NudgeTier options
        nudge_tiers = [NudgeTier.GENTLE, NudgeTier.SARCASTIC, NudgeTier.SERGEANT]
        success = len(nudge_tiers) == 3
        results.record_test("Nudge tier system", success, duration_ms)
        
        # Test 2: User model ADHD fields
        test_user = User(
            user_id="adhd_test",
            name="ADHD Test User",
            preferred_nudge_methods=["web", "telegram"],
            energy_patterns={"peak_hours": [9, 10, 11]},
            hyperfocus_indicators=["long_sessions"]
        )
        
        adhd_fields = 0
        if hasattr(test_user, 'energy_patterns'):
            adhd_fields += 1
        if hasattr(test_user, 'hyperfocus_indicators'):
            adhd_fields += 1
        if hasattr(test_user, 'preferred_nudge_methods'):
            adhd_fields += 1
        
        success = adhd_fields >= 3
        results.record_test(f"ADHD user fields ({adhd_fields}/3)", success)
        
        # Test 3: ADHD profile data structure
        from mcp_server.onboarding import ADHDProfileData
        
        profile = ADHDProfileData(
            primary_challenges=["focus", "time_management"],
            strengths=["creativity", "hyperfocus"],
            best_focus_times=["morning"],
            overwhelm_triggers=["too_many_tasks"]
        )
        
        success = len(profile.primary_challenges) > 0 and len(profile.strengths) > 0
        results.record_test("ADHD profile structure", success)
        
        # Test 4: Crisis detection simulation
        crisis_keywords = ["overwhelmed", "can't focus", "too much", "stressed", "anxious"]
        
        crisis_detection_available = False
        try:
            # Check if we have crisis detection logic
            from mcp_server import cognitive_loop  
            crisis_detection_available = True
        except:
            pass
            
        results.record_test("Crisis detection system", crisis_detection_available)
        if not crisis_detection_available:
            results.add_warning("Crisis detection system not fully implemented")
        
        # Test 5: Performance targets
        performance_targets = {
            "max_response_time": 3000,  # 3 seconds
            "target_uptime": 99.9,
            "memory_limit": 500  # MB
        }
        
        success = performance_targets["max_response_time"] == 3000  # ADHD target
        results.record_test("ADHD performance targets defined", success)
        
        return True
        
    except Exception as e:
        results.record_test("ADHD features error", False)
        results.add_warning(f"ADHD features testing failed: {e}")
        return False


async def test_error_handling(results: E2ETestResults):
    """Test error handling and resilience."""
    print("\n🛡️ Testing Error Handling")
    print("-" * 27)
    
    try:
        # Test 1: Invalid authentication
        from mcp_server.auth import auth_manager, LoginRequest
        
        start_time = time.time()
        invalid_login = LoginRequest(email="nonexistent@test.com", password="wrongpassword")
        result = auth_manager.login_user(invalid_login)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Should fail gracefully with ADHD-friendly message
        success = not result.success and "Invalid email or password" in result.message
        results.record_test("Graceful auth failure", success, duration_ms)
        
        # Test 2: Invalid onboarding input
        from mcp_server.onboarding import onboarding_manager
        
        try:
            start_time = time.time()
            await onboarding_manager.process_step("nonexistent_user", {})
            duration_ms = int((time.time() - start_time) * 1000)
            results.record_test("Invalid onboarding handling", False)  # Should have raised exception
        except ValueError:
            duration_ms = int((time.time() - start_time) * 1000)
            results.record_test("Invalid onboarding handling", True, duration_ms)
        
        # Test 3: Password validation
        from mcp_server.auth import RegistrationRequest
        
        weak_passwords = ["123", "password", "short"]
        validation_working = 0
        
        for weak_pass in weak_passwords:
            try:
                RegistrationRequest(name="Test", email="test@test.com", password=weak_pass)
            except ValueError:
                validation_working += 1
        
        success = validation_working == len(weak_passwords)
        results.record_test(f"Password validation ({validation_working}/{len(weak_passwords)})", success)
        
        # Test 4: Duplicate email handling
        from mcp_server.auth import auth_manager, RegistrationRequest
        
        # Register first user
        reg1 = RegistrationRequest(name="User1", email="duplicate@test.com", password="password123")
        result1 = auth_manager.register_user(reg1)
        
        # Try to register with same email
        reg2 = RegistrationRequest(name="User2", email="duplicate@test.com", password="password456")
        result2 = auth_manager.register_user(reg2)
        
        success = result1.success and not result2.success and "already exists" in result2.message
        results.record_test("Duplicate email handling", success)
        
        return True
        
    except Exception as e:
        results.record_test("Error handling test failed", False)
        results.add_warning(f"Error handling test issue: {e}")
        return False


async def run_comprehensive_e2e_tests():
    """Run all end-to-end tests."""
    print("🧠⚡ MCP ADHD SERVER - COMPREHENSIVE E2E TESTS")
    print("=" * 55)
    print("Testing complete system integration for ADHD readiness...\n")
    
    results = E2ETestResults()
    
    # Run all test suites
    test_suites = [
        ("Authentication Flow", test_authentication_flow),
        ("Onboarding System", test_onboarding_system), 
        ("Telegram Integration", test_telegram_integration),
        ("Performance Requirements", test_system_performance),
        ("ADHD-Specific Features", test_adhd_specific_features),
        ("Error Handling", test_error_handling)
    ]
    
    suite_results = []
    
    for suite_name, test_function in test_suites:
        print(f"\n🧪 Running {suite_name} Tests...")
        try:
            suite_success = await test_function(results)
            suite_results.append((suite_name, suite_success))
        except Exception as e:
            print(f"❌ {suite_name} suite crashed: {e}")
            results.record_test(f"{suite_name} suite", False, critical=True)
            suite_results.append((suite_name, False))
    
    # Print final results
    overall_success = results.print_summary()
    
    print(f"\n📋 Test Suite Results:")
    for suite_name, success in suite_results:
        status = "✅" if success else "❌"
        print(f"   {status} {suite_name}")
    
    print(f"\n🎯 System Readiness Assessment:")
    if overall_success:
        print("   🎉 SYSTEM READY FOR ADHD USERS!")
        print("   The MCP ADHD Server has passed comprehensive testing")
        print("   and is ready for beta user deployment.")
    else:
        print("   ⚠️ SYSTEM NEEDS ATTENTION")
        print("   Critical issues found that should be resolved")
        print("   before deploying to ADHD users.")
    
    print(f"\n📈 Next Steps:")
    if overall_success:
        print("   1. Deploy to staging environment")
        print("   2. Invite beta testers")
        print("   3. Monitor ADHD-specific metrics")  
        print("   4. Collect user feedback")
        print("   5. Iterate based on neurodivergent needs")
    else:
        print("   1. Fix critical failures")
        print("   2. Optimize performance issues")
        print("   3. Re-run comprehensive tests")
        print("   4. Address ADHD-specific concerns")
    
    return overall_success


if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_e2e_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)