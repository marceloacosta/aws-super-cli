#!/usr/bin/env python3
"""Simple test script to verify the empty error box fix"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock being in a test environment
sys.modules['pytest'] = type(sys)('pytest')

from typer.testing import CliRunner
from aws_super_cli.cli import app

def test_empty_error_box_fix():
    """Test that running aws-super-cli without args shows clean help output"""
    runner = CliRunner()
    
    # Test the main issue: running without arguments
    result = runner.invoke(app, [])
    
    print("Exit code:", result.exit_code)
    print("Output length:", len(result.stdout))
    print("First 200 chars of output:")
    print(repr(result.stdout[:200]))
    
    # Check for basic functionality
    assert "Usage:" in result.stdout, "Should show usage info"
    assert "aws-super-cli" in result.stdout, "Should show app name"
    
    # Check that Rich markup is NOT present (the key fix)
    assert "[cyan]" not in result.stdout, "Should not have Rich markup leakage"
    assert "[bold]" not in result.stdout, "Should not have Rich markup leakage"
    
    print("✅ Empty error box issue appears to be fixed!")
    return True

def test_help_command_clean():
    """Test that the help command produces clean output"""
    runner = CliRunner()
    
    # Test the help command
    result = runner.invoke(app, ["help"])
    
    print("\nHelp command test:")
    print("Exit code:", result.exit_code)
    print("Output length:", len(result.stdout))
    
    # Check for basic functionality
    assert result.exit_code == 0, "Help command should succeed"
    assert "AWS Super CLI" in result.stdout, "Should show app name"
    
    # Check that Rich markup is NOT present (the key fix)
    assert "[cyan]" not in result.stdout, "Help should not have Rich markup leakage"
    assert "[bold]" not in result.stdout, "Help should not have Rich markup leakage"
    
    print("✅ Help command clean output verified!")
    return True

def test_help_flag_clean():
    """Test that the -h flag produces clean output"""
    runner = CliRunner()
    
    # Test the -h flag
    result = runner.invoke(app, ["-h"])
    
    print("\n-h flag test:")
    print("Exit code:", result.exit_code)
    print("Output length:", len(result.stdout))
    
    # Check for basic functionality
    assert result.exit_code == 0, "Help flag should succeed"
    assert "AWS Super CLI" in result.stdout, "Should show app name"
    
    # Check that Rich markup is NOT present (the key fix)
    assert "[cyan]" not in result.stdout, "-h flag should not have Rich markup leakage"
    assert "[bold]" not in result.stdout, "-h flag should not have Rich markup leakage"
    
    print("✅ -h flag clean output verified!")
    return True

if __name__ == "__main__":
    try:
        test_empty_error_box_fix()
        test_help_command_clean()
        test_help_flag_clean()
        print("\n🎉 All tests passed! Issue #4 appears to be resolved.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1) 