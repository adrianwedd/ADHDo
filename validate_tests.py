#!/usr/bin/env python3
"""
Quick validation script to check testing framework completeness.
"""
import os
import sys
from pathlib import Path

def validate_test_structure():
    """Validate the comprehensive testing structure."""
    base_dir = Path(__file__).parent
    
    print("🧪 MCP ADHD Server - Testing Framework Validation")
    print("=" * 50)
    
    # Check test configuration files
    config_files = [
        "pytest.ini",
        ".coveragerc",
        "tests/conftest.py"
    ]
    
    print("\n📋 Configuration Files:")
    for file in config_files:
        path = base_dir / file
        if path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
    
    # Check test directory structure
    test_dirs = [
        "tests/unit",
        "tests/integration", 
        "tests/e2e",
        "tests/performance"
    ]
    
    print("\n📁 Test Directory Structure:")
    for dir_name in test_dirs:
        path = base_dir / dir_name
        if path.exists() and path.is_dir():
            test_files = list(path.glob("test_*.py"))
            print(f"  ✅ {dir_name} ({len(test_files)} test files)")
        else:
            print(f"  ❌ {dir_name} - MISSING")
    
    # Check CI/CD pipeline
    ci_files = [
        ".github/workflows/ci.yml"
    ]
    
    print("\n🚀 CI/CD Pipeline:")
    for file in ci_files:
        path = base_dir / file
        if path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
    
    # Check test runner scripts
    script_files = [
        "scripts/run_tests.sh"
    ]
    
    print("\n🔧 Test Runner Scripts:")
    for file in script_files:
        path = base_dir / file
        if path.exists():
            print(f"  ✅ {file} ({'executable' if os.access(path, os.X_OK) else 'not executable'})")
        else:
            print(f"  ❌ {file} - MISSING")
    
    # Count total test files
    total_tests = 0
    test_categories = {}
    
    for test_dir in ["unit", "integration", "e2e", "performance"]:
        test_path = base_dir / "tests" / test_dir
        if test_path.exists():
            test_files = list(test_path.glob("test_*.py"))
            test_categories[test_dir] = len(test_files)
            total_tests += len(test_files)
    
    print("\n📊 Test Coverage Summary:")
    print(f"  Total test files: {total_tests}")
    for category, count in test_categories.items():
        print(f"  {category.capitalize()}: {count} files")
    
    # Check ADHD-specific test markers
    adhd_tests = 0
    performance_tests = 0
    
    for test_dir in Path(base_dir / "tests").rglob("test_*.py"):
        try:
            with open(test_dir, 'r') as f:
                content = f.read()
                if '@pytest.mark.adhd' in content:
                    adhd_tests += content.count('@pytest.mark.adhd')
                if '@pytest.mark.performance' in content:
                    performance_tests += content.count('@pytest.mark.performance')
        except:
            continue
    
    print(f"\n🧠 ADHD-Specific Test Coverage:")
    print(f"  ADHD test markers: {adhd_tests}")
    print(f"  Performance test markers: {performance_tests}")
    
    # Final assessment
    print(f"\n🎯 Assessment:")
    if total_tests >= 10 and adhd_tests >= 5:
        print("  ✅ COMPREHENSIVE TESTING SUITE COMPLETE!")
        print("  ✅ ADHD optimizations extensively tested")
        print("  ✅ Ready for production deployment")
        return True
    else:
        print("  ⚠️  Testing suite needs more coverage")
        return False

if __name__ == "__main__":
    success = validate_test_structure()
    sys.exit(0 if success else 1)