#!/usr/bin/env python3
"""
AWS Super CLI Test Runner

Runs the complete test suite including:
- Unit tests for CLI commands
- Regression tests for known issues
- Integration tests (mocked)
- Output formatting tests

Usage:
  python run_tests.py              # Run all tests
  python run_tests.py --regression # Run only regression tests
  python run_tests.py --verbose    # Run with verbose output
  python run_tests.py --coverage   # Run with coverage report
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, capture_output=False):
    """Run a command and return the result"""
    print(f"🔄 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    return result


def check_dependencies():
    """Check if required test dependencies are installed"""
    required = ['pytest', 'pytest-asyncio', 'pytest-cov']
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing test dependencies: {', '.join(missing)}")
        print(f"💡 Install with: pip install {' '.join(missing)}")
        return False
    
    return True


def run_tests(test_type='all', verbose=False, coverage=False):
    """Run the specified tests"""
    
    if not check_dependencies():
        return False
    
    # Base pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test selection
    if test_type == 'regression':
        cmd.append('tests/test_regression.py')
    elif test_type == 'cli':
        cmd.append('tests/test_cli.py')
    else:
        cmd.append('tests/')
    
    # Add options
    if verbose:
        cmd.extend(['-v', '-s'])
    else:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=aws_super_cli',
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
    
    # Add async support
    cmd.append('-p')
    cmd.append('asyncio')
    
    print("🧪 AWS Super CLI Test Suite")
    print("=" * 50)
    
    result = run_command(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        if coverage:
            print("📊 Coverage report generated in htmlcov/")
        return True
    else:
        print(f"\n❌ Tests failed with exit code {result.returncode}")
        return False


def run_quick_smoke_tests():
    """Run a quick smoke test to verify basic functionality"""
    print("🔥 Running quick smoke tests...")
    
    smoke_tests = [
        ['python', '-c', 'from aws_super_cli.cli import app; print("✓ CLI imports successfully")'],
        ['python', '-c', 'from aws_super_cli.aws import aws_session; print("✓ AWS session imports successfully")'],
        ['aws-super-cli', '--help'],
    ]
    
    for i, cmd in enumerate(smoke_tests, 1):
        print(f"  {i}. {' '.join(cmd[:3])}...")
        result = run_command(cmd, capture_output=True)
        if result.returncode != 0:
            print(f"    ❌ Failed: {result.stderr}")
            return False
        else:
            print(f"    ✅ Passed")
    
    return True


def run_regression_verification():
    """Run specific regression tests to verify recent fixes"""
    print("🔍 Running regression verification...")
    
    # Test the Rich markup fix specifically
    cmd = [
        'python', '-c', 
        '''
from typer.testing import CliRunner
from aws_super_cli.cli import app
runner = CliRunner()
result = runner.invoke(app, ["help"])
assert "[cyan]" not in result.stdout, "Rich markup regression detected!"
assert "AWS Super CLI" in result.stdout
print("✓ Rich markup regression test passed")
        '''
    ]
    
    result = run_command(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Regression test failed: {result.stderr}")
        return False
    else:
        print("✅ Regression verification passed")
        return True


def main():
    parser = argparse.ArgumentParser(description='AWS Super CLI Test Runner')
    parser.add_argument('--regression', action='store_true', 
                       help='Run only regression tests')
    parser.add_argument('--cli', action='store_true', 
                       help='Run only CLI tests')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose output')
    parser.add_argument('--coverage', '-c', action='store_true', 
                       help='Generate coverage report')
    parser.add_argument('--smoke', action='store_true', 
                       help='Run only quick smoke tests')
    parser.add_argument('--verify-regression', action='store_true', 
                       help='Verify recent regression fixes')
    
    args = parser.parse_args()
    
    # Determine test type
    if args.regression:
        test_type = 'regression'
    elif args.cli:
        test_type = 'cli'
    else:
        test_type = 'all'
    
    # Run appropriate tests
    if args.smoke:
        success = run_quick_smoke_tests()
    elif args.verify_regression:
        success = run_regression_verification()
    else:
        success = run_tests(test_type, args.verbose, args.coverage)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 