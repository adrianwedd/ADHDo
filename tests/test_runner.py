"""
Comprehensive Test Runner for ADHD Safety and Core Systems

This test runner executes the complete test suite with proper prioritization:
1. LIFE-CRITICAL tests (crisis detection, safety responses) - MUST PASS
2. CORE SYSTEM tests (authentication, cognitive loop) - HIGH PRIORITY  
3. PERFORMANCE tests (ADHD-specific response times) - MEDIUM PRIORITY
4. SCENARIO tests (user journeys, integration) - VALIDATION

Usage:
    python tests/test_runner.py --safety-only     # Run only life-critical safety tests
    python tests/test_runner.py --core-only       # Run core system tests
    python tests/test_runner.py --performance     # Run performance tests
    python tests/test_runner.py --full           # Run complete test suite
    python tests/test_runner.py --coverage       # Run with coverage reporting
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
from dataclasses import dataclass
from enum import Enum

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPriority(Enum):
    """Test priority levels for ADHD safety system."""
    LIFE_CRITICAL = 1  # Crisis detection, safety responses - MUST PASS
    CORE_SYSTEM = 2    # Authentication, cognitive loop - HIGH PRIORITY
    PERFORMANCE = 3    # ADHD response times, load testing - MEDIUM PRIORITY 
    SCENARIO = 4       # User journeys, integration - VALIDATION


@dataclass
class TestSuite:
    """Test suite configuration."""
    name: str
    priority: TestPriority
    test_paths: List[str]
    description: str
    timeout_seconds: int = 300
    required_pass_rate: float = 1.0  # 100% pass rate required for life-critical


class ADHDTestRunner:
    """Comprehensive test runner for ADHD safety system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent
        
        # Define test suites with proper prioritization
        self.test_suites = {
            "safety_critical": TestSuite(
                name="Life-Critical Safety Tests",
                priority=TestPriority.LIFE_CRITICAL,
                test_paths=[
                    "tests/unit/safety/test_crisis_detection.py",
                    "tests/unit/safety/test_safety_response_validation.py", 
                    "tests/unit/safety/test_emergency_access.py"
                ],
                description="Crisis detection and safety intervention tests - MUST PASS",
                timeout_seconds=120,
                required_pass_rate=1.0
            ),
            
            "circuit_breaker": TestSuite(
                name="Circuit Breaker Protection",
                priority=TestPriority.LIFE_CRITICAL,
                test_paths=[
                    "tests/unit/safety/test_circuit_breaker.py"
                ],
                description="ADHD psychological safety circuit breaker tests",
                timeout_seconds=180,
                required_pass_rate=1.0
            ),
            
            "authentication_security": TestSuite(
                name="Authentication Security",
                priority=TestPriority.CORE_SYSTEM,
                test_paths=[
                    "tests/unit/security/test_auth_security.py"
                ],
                description="Authentication system security and attack vector testing",
                timeout_seconds=300,
                required_pass_rate=0.95
            ),
            
            "cognitive_loop": TestSuite(
                name="Cognitive Loop Integration", 
                priority=TestPriority.CORE_SYSTEM,
                test_paths=[
                    "tests/integration/test_cognitive_loop_integration.py"
                ],
                description="End-to-end cognitive loop processing tests",
                timeout_seconds=240,
                required_pass_rate=0.90
            ),
            
            "performance_adhd": TestSuite(
                name="ADHD Performance Requirements",
                priority=TestPriority.PERFORMANCE,
                test_paths=[
                    "tests/performance/test_adhd_performance_load.py"
                ],
                description="ADHD-specific performance and load testing",
                timeout_seconds=600,
                required_pass_rate=0.85
            ),
            
            "user_scenarios": TestSuite(
                name="ADHD User Scenarios",
                priority=TestPriority.SCENARIO,
                test_paths=[
                    "tests/e2e/test_adhd_user_scenarios.py"
                ],
                description="Realistic ADHD user journey testing",
                timeout_seconds=360,
                required_pass_rate=0.80
            ),
            
            "existing_tests": TestSuite(
                name="Existing Test Suite",
                priority=TestPriority.CORE_SYSTEM,
                test_paths=[
                    "tests/unit/",
                    "tests/integration/", 
                    "tests/e2e/"
                ],
                description="Existing unit, integration and e2e tests",
                timeout_seconds=480,
                required_pass_rate=0.85
            )
        }
    
    def run_test_suite(self, suite: TestSuite, coverage: bool = False, verbose: bool = True) -> Tuple[bool, Dict]:
        """Run a specific test suite."""
        print(f"\n{'='*60}")
        print(f"🧪 Running {suite.name}")
        print(f"Priority: {suite.priority.name}")
        print(f"Description: {suite.description}")
        print(f"Required Pass Rate: {suite.required_pass_rate*100:.0f}%")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])
        
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # Add timeout
        cmd.extend(["--timeout", str(suite.timeout_seconds)])
        
        # Add test paths
        for test_path in suite.test_paths:
            full_path = self.project_root / test_path
            if full_path.exists():
                cmd.append(str(full_path))
            else:
                print(f"⚠️  Warning: Test path not found: {test_path}")
        
        # Run tests
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=suite.timeout_seconds + 30  # Extra buffer
            )
            
            duration = time.time() - start_time
            
            # Parse results
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')
            
            # Extract test results
            passed = 0
            failed = 0
            skipped = 0
            
            for line in output_lines + error_lines:
                if " passed" in line and " failed" in line:
                    # Format: "X failed, Y passed in Zs"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed,":
                            failed = int(parts[i-1])
                        elif part == "passed":
                            passed = int(parts[i-1])
                elif " passed in " in line and " failed" not in line:
                    # Format: "X passed in Zs"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            passed = int(parts[i-1])
                elif " skipped" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "skipped":
                            skipped = int(parts[i-1])
            
            total_tests = passed + failed + skipped
            pass_rate = passed / total_tests if total_tests > 0 else 0.0
            
            # Determine success based on requirements
            success = (
                result.returncode == 0 and 
                pass_rate >= suite.required_pass_rate and
                failed == 0 if suite.priority == TestPriority.LIFE_CRITICAL else True
            )
            
            results = {
                "success": success,
                "return_code": result.returncode,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total": total_tests,
                "pass_rate": pass_rate,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            # Print results
            if success:
                print(f"✅ {suite.name} PASSED")
            else:
                print(f"❌ {suite.name} FAILED")
                if suite.priority == TestPriority.LIFE_CRITICAL:
                    print(f"🚨 CRITICAL FAILURE: Life-critical safety tests failed!")
            
            print(f"📊 Results: {passed} passed, {failed} failed, {skipped} skipped")
            print(f"📈 Pass Rate: {pass_rate*100:.1f}% (required: {suite.required_pass_rate*100:.0f}%)")
            print(f"⏱️  Duration: {duration:.1f}s")
            
            if failed > 0 and verbose:
                print(f"\n❌ Failed Test Details:")
                print(result.stdout)
                if result.stderr:
                    print(f"\n🔍 Error Details:")
                    print(result.stderr)
            
            return success, results
            
        except subprocess.TimeoutExpired:
            print(f"⏰ Test suite timed out after {suite.timeout_seconds}s")
            return False, {"success": False, "timeout": True, "duration": suite.timeout_seconds}
        
        except Exception as e:
            print(f"💥 Test suite failed with exception: {e}")
            return False, {"success": False, "exception": str(e), "duration": time.time() - start_time}
    
    def run_safety_critical_only(self, coverage: bool = False) -> bool:
        """Run only life-critical safety tests."""
        print("🚨 Running LIFE-CRITICAL Safety Tests Only")
        print("These tests MUST pass for user safety!")
        
        critical_suites = [
            self.test_suites["safety_critical"],
            self.test_suites["circuit_breaker"]
        ]
        
        all_passed = True
        for suite in critical_suites:
            success, _ = self.run_test_suite(suite, coverage=coverage)
            if not success:
                all_passed = False
                if suite.priority == TestPriority.LIFE_CRITICAL:
                    print(f"\n🚨 CRITICAL SAFETY FAILURE in {suite.name}")
                    print("❌ System is NOT safe for ADHD users!")
                    break
        
        return all_passed
    
    def run_core_system_only(self, coverage: bool = False) -> bool:
        """Run core system tests."""
        print("🏗️  Running Core System Tests")
        
        core_suites = [
            self.test_suites["authentication_security"],
            self.test_suites["cognitive_loop"]
        ]
        
        all_passed = True
        for suite in core_suites:
            success, _ = self.run_test_suite(suite, coverage=coverage)
            if not success:
                all_passed = False
        
        return all_passed
    
    def run_performance_tests(self, coverage: bool = False) -> bool:
        """Run ADHD performance tests."""
        print("⚡ Running ADHD Performance Tests")
        
        performance_suites = [
            self.test_suites["performance_adhd"]
        ]
        
        all_passed = True
        for suite in performance_suites:
            success, _ = self.run_test_suite(suite, coverage=coverage)
            if not success:
                all_passed = False
        
        return all_passed
    
    def run_full_test_suite(self, coverage: bool = False, stop_on_critical_failure: bool = True) -> Dict:
        """Run complete test suite with proper prioritization."""
        print("🎯 Running Complete ADHD Safety Test Suite")
        print("Testing life-critical safety systems and core functionality")
        
        start_time = time.time()
        results = {}
        
        # Sort suites by priority
        sorted_suites = sorted(
            self.test_suites.items(),
            key=lambda x: x[1].priority.value
        )
        
        critical_failures = 0
        total_passed = 0
        total_failed = 0
        
        for suite_name, suite in sorted_suites:
            print(f"\n📋 Running {suite_name}...")
            
            success, suite_results = self.run_test_suite(suite, coverage=coverage)
            results[suite_name] = suite_results
            
            if "passed" in suite_results:
                total_passed += suite_results["passed"]
                total_failed += suite_results["failed"]
            
            if not success:
                if suite.priority == TestPriority.LIFE_CRITICAL:
                    critical_failures += 1
                    print(f"\n🚨 CRITICAL FAILURE: {suite.name}")
                    
                    if stop_on_critical_failure:
                        print("❌ Stopping test run due to critical safety failure!")
                        break
        
        total_duration = time.time() - start_time
        
        # Final results
        print(f"\n{'='*60}")
        print(f"🏁 COMPLETE TEST SUITE RESULTS")
        print(f"{'='*60}")
        
        if critical_failures == 0:
            print(f"✅ All life-critical safety tests PASSED")
            print(f"✅ System is SAFE for ADHD users")
        else:
            print(f"❌ {critical_failures} critical safety failures detected")
            print(f"🚨 System is NOT SAFE for ADHD users until fixed!")
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Tests: {total_passed + total_failed}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        if total_passed + total_failed > 0:
            overall_pass_rate = total_passed / (total_passed + total_failed)
            print(f"   Pass Rate: {overall_pass_rate*100:.1f}%")
        print(f"   Duration: {total_duration:.1f}s")
        print(f"   Critical Failures: {critical_failures}")
        
        results["summary"] = {
            "critical_failures": critical_failures,
            "total_passed": total_passed, 
            "total_failed": total_failed,
            "duration": total_duration,
            "safe_for_users": critical_failures == 0
        }
        
        return results
    
    def generate_coverage_report(self):
        """Generate comprehensive coverage report."""
        print("📈 Generating Coverage Report...")
        
        cmd = [
            "python", "-m", "pytest",
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=term-missing",
            "tests/"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            print("✅ Coverage report generated!")
            print("📄 HTML report: htmlcov/index.html")
            print("📄 XML report: coverage.xml")
            
            # Extract coverage percentage
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    print(f"📊 {line}")
            
        except Exception as e:
            print(f"❌ Coverage report failed: {e}")
    
    def validate_test_environment(self) -> bool:
        """Validate test environment setup."""
        print("🔍 Validating Test Environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            print(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
            return False
        
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check required packages
        required_packages = ["pytest", "pytest-asyncio", "pytest-cov", "pytest-mock"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"❌ {package} not found")
        
        if missing_packages:
            print(f"\n💡 Install missing packages:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
        
        # Check test files exist
        missing_tests = []
        for suite_name, suite in self.test_suites.items():
            for test_path in suite.test_paths:
                full_path = self.project_root / test_path
                if not full_path.exists():
                    missing_tests.append(test_path)
        
        if missing_tests:
            print(f"\n❌ Missing test files:")
            for test_path in missing_tests:
                print(f"   {test_path}")
            return False
        
        print("✅ Test environment validated!")
        return True


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="ADHD Safety System Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/test_runner.py --safety-only    # Run only life-critical tests
    python tests/test_runner.py --full          # Run complete test suite  
    python tests/test_runner.py --coverage      # Run with coverage report
    python tests/test_runner.py --validate      # Validate test environment
        """
    )
    
    parser.add_argument(
        "--safety-only", 
        action="store_true",
        help="Run only life-critical safety tests (crisis detection, safety responses)"
    )
    
    parser.add_argument(
        "--core-only",
        action="store_true", 
        help="Run only core system tests (authentication, cognitive loop)"
    )
    
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run ADHD performance and load tests"
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete test suite with proper prioritization"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate test environment setup"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    runner = ADHDTestRunner()
    
    # Validate environment first
    if args.validate or not any([args.safety_only, args.core_only, args.performance, args.full, args.coverage]):
        if not runner.validate_test_environment():
            sys.exit(1)
        if args.validate:
            return
    
    success = True
    
    try:
        if args.safety_only:
            success = runner.run_safety_critical_only(coverage=args.coverage)
            
        elif args.core_only:
            success = runner.run_core_system_only(coverage=args.coverage)
            
        elif args.performance:
            success = runner.run_performance_tests(coverage=args.coverage)
            
        elif args.full:
            results = runner.run_full_test_suite(coverage=args.coverage)
            success = results["summary"]["safe_for_users"]
            
        elif args.coverage:
            runner.generate_coverage_report()
            
        else:
            # Default: run safety critical tests
            print("No test mode specified, running life-critical safety tests...")
            success = runner.run_safety_critical_only(coverage=False)
        
        if not success:
            print(f"\n🚨 TEST FAILURES DETECTED!")
            if args.safety_only or args.full:
                print(f"❌ System may not be safe for ADHD users!")
                print(f"🔧 Fix critical failures before deployment!")
            sys.exit(1)
        else:
            print(f"\n✅ All required tests passed!")
            if args.safety_only or args.full:
                print(f"✅ System is safe for ADHD users!")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Test run interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()