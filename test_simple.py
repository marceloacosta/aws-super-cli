#!/usr/bin/env python3
"""Simple test to verify the empty error box fix without external dependencies"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Signal that we're in test mode
os.environ['TEST_MODE'] = '1'

# Test the helper functions directly
from aws_super_cli.cli import should_use_clean_output, safe_print

def test_clean_output_detection():
    """Test that we detect test environments correctly"""
    result = should_use_clean_output()
    print(f"should_use_clean_output() returned: {result}")
    assert result == True, "Should detect test environment"
    print("✅ Clean output detection working!")

def test_safe_print_strips_markup():
    """Test that safe_print strips Rich markup in test environments"""
    print("\nTesting safe_print with Rich markup:")
    
    # Capture output
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        safe_print("[cyan]Hello[/cyan] [bold]World[/bold]")
    
    output = f.getvalue()
    print(f"safe_print output: {repr(output)}")
    
    # Check that markup is stripped
    assert "[cyan]" not in output, "Should not contain [cyan] markup"
    assert "[bold]" not in output, "Should not contain [bold] markup"
    assert "Hello World" in output, "Should contain the actual text"
    
    print("✅ safe_print markup stripping working!")

def test_safe_print_empty_string():
    """Test that safe_print handles empty strings correctly"""
    print("\nTesting safe_print with empty string:")
    
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        safe_print("")
    
    output = f.getvalue()
    print(f"Empty string output: {repr(output)}")
    
    # Should just be a newline
    assert output == "\n", "Empty string should produce just a newline"
    
    print("✅ safe_print empty string handling working!")

if __name__ == "__main__":
    try:
        test_clean_output_detection()
        test_safe_print_strips_markup()
        test_safe_print_empty_string()
        print("\n🎉 All tests passed! Issue #4 fix is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 