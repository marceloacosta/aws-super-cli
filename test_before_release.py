#!/usr/bin/env python3
"""
Pre-Release Test Suite for AWS Super CLI

Comprehensive test suite to run before releasing a new version.
This includes:
- All unit and regression tests
- CLI functionality verification
- Output format validation
- Integration smoke tests

Usage:
  python test_before_release.py

Returns exit code 0 if all tests pass, 1 if any fail.
"""

import subprocess
import sys
import json
from datetime import datetime


def run_command(cmd, capture_output=True):
    """Run a command and return the result"""
    print(f"🔄 {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    return result


def test_cli_basic_functionality():
    """Test basic CLI functionality without AWS credentials"""
    print("\n📋 Testing CLI Basic Functionality")
    print("=" * 50)
    
    tests = [
        # Help commands should work
        (['aws-super-cli', '--help'], "Help flag"),
        (['aws-super-cli', 'help'], "Help command"),
        (['aws-super-cli', 'ls', '--help'], "LS help"),
        (['aws-super-cli', 'cost', '--help'], "Cost help"),
        (['aws-super-cli', 'audit', '--help'], "Audit help"),
        
        # Version should work
        (['aws-super-cli', 'version'], "Version command"),
        
        # Commands without args should show helpful menus
        (['aws-super-cli', 'ls'], "LS without args"),
        (['aws-super-cli', 'cost'], "Cost without args"),
        
        # Invalid services should be handled gracefully
        (['aws-super-cli', 'ls', 'invalid'], "Invalid service"),
        (['aws-super-cli', 'cost', 'invalid'], "Invalid cost command"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, description in tests:
        result = run_command(cmd)
        
        if result.returncode in [0, 2]:  # 0 = success, 2 = expected typer behavior
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description} (exit code: {result.returncode})")
            print(f"     Error: {result.stderr[:100]}...")
            failed += 1
    
    print(f"\n📊 CLI Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_rich_formatting():
    """Test that Rich markup is properly rendered"""
    print("\n🎨 Testing Rich Output Formatting")
    print("=" * 50)
    
    # Test help command doesn't leak markup
    result = run_command(['aws-super-cli', 'help'])
    
    if "[cyan]" in result.stdout or "[bold]" in result.stdout:
        print("  ❌ Rich markup regression detected!")
        print("     Found literal markup tags in output")
        return False
    
    if "AWS Super CLI" not in result.stdout:
        print("  ❌ Help content missing")
        return False
    
    print("  ✅ Rich markup properly rendered")
    print("  ✅ Help content present")
    return True


def test_service_aliases():
    """Test that service aliases work correctly"""
    print("\n🔄 Testing Service Aliases")
    print("=" * 50)
    
    aliases_to_test = [
        'instances',
        'buckets', 
        'databases',
        'functions'
    ]
    
    passed = 0
    for alias in aliases_to_test:
        result = run_command(['aws-super-cli', 'ls', alias])
        
        if result.returncode == 0:
            print(f"  ✅ Alias '{alias}' recognized")
            passed += 1
        else:
            print(f"  ❌ Alias '{alias}' failed")
    
    print(f"\n📊 Alias Tests: {passed}/{len(aliases_to_test)} passed")
    return passed == len(aliases_to_test)


def run_pytest_suite():
    """Run the full pytest suite"""
    print("\n🧪 Running Pytest Suite")
    print("=" * 50)
    
    result = run_command(['python', '-m', 'pytest', 'tests/', '-v', '--tb=short'])
    
    if result.returncode == 0:
        print("  ✅ All pytest tests passed")
        return True
    else:
        print(f"  ❌ Pytest failed with exit code {result.returncode}")
        return False


def test_import_integrity():
    """Test that all modules can be imported without errors"""
    print("\n📦 Testing Import Integrity")
    print("=" * 50)
    
    imports_to_test = [
        'from awsx.cli import app',
        'from awsx.aws import aws_session',
        'from awsx.services import ec2, s3, vpc, rds, elb, iam',
        'from awsx.services import cost, audit',
    ]
    
    passed = 0
    for import_stmt in imports_to_test:
        result = run_command(['python', '-c', import_stmt])
        
        if result.returncode == 0:
            print(f"  ✅ {import_stmt}")
            passed += 1
        else:
            print(f"  ❌ {import_stmt}")
            print(f"     Error: {result.stderr}")
    
    print(f"\n📊 Import Tests: {passed}/{len(imports_to_test)} passed")
    return passed == len(imports_to_test)


def generate_test_report(results):
    """Generate a test report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = {
        "timestamp": timestamp,
        "overall_status": "PASS" if all(results.values()) else "FAIL",
        "test_results": results,
        "summary": {
            "total_test_categories": len(results),
            "passed_categories": sum(1 for r in results.values() if r),
            "failed_categories": sum(1 for r in results.values() if not r)
        }
    }
    
    print("\n" + "=" * 60)
    print("📋 PRE-RELEASE TEST REPORT")
    print("=" * 60)
    print(f"Timestamp: {timestamp}")
    print(f"Overall Status: {report['overall_status']}")
    print()
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print()
    print(f"Summary: {report['summary']['passed_categories']}/{report['summary']['total_test_categories']} test categories passed")
    
    if report['overall_status'] == "PASS":
        print("\n🎉 All tests passed! Ready for release.")
    else:
        print("\n⚠️  Some tests failed. Fix issues before release.")
    
    return report['overall_status'] == "PASS"


def main():
    """Run all pre-release tests"""
    print("🚀 AWS Super CLI Pre-Release Test Suite")
    print("=" * 60)
    
    # Run all test categories
    results = {
        "Import Integrity": test_import_integrity(),
        "CLI Basic Functionality": test_cli_basic_functionality(), 
        "Rich Formatting": test_rich_formatting(),
        "Service Aliases": test_service_aliases(),
        "Pytest Suite": run_pytest_suite(),
    }
    
    # Generate report and exit
    success = generate_test_report(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 