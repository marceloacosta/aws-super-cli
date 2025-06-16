#!/usr/bin/env python3
"""
Test version consistency verification functionality
"""

import unittest
import subprocess
import sys
from pathlib import Path

class TestVersionConsistency(unittest.TestCase):
    """Test version consistency verification"""
    
    def setUp(self):
        """Set up test environment"""
        self.script_path = Path(__file__).parent.parent / "scripts" / "verify_version_consistency.py"
        
    def test_version_script_exists(self):
        """Test that the version verification script exists and is executable"""
        self.assertTrue(self.script_path.exists(), "Version verification script should exist")
        self.assertTrue(self.script_path.is_file(), "Version verification script should be a file")
        
    def test_version_verification_runs(self):
        """Test that the version verification script runs without errors"""
        try:
            result = subprocess.run([
                sys.executable, str(self.script_path)
            ], capture_output=True, text=True, timeout=30)
            
            # Should complete successfully (exit code 0 means versions are consistent)
            self.assertEqual(result.returncode, 0, 
                           f"Version verification failed: {result.stderr}")
            
            # Should contain expected output
            self.assertIn("Running Version Consistency Verification", result.stdout)
            self.assertIn("VERSION VERIFICATION PASSED", result.stdout)
            
        except subprocess.TimeoutExpired:
            self.fail("Version verification script timed out")
        except Exception as e:
            self.fail(f"Version verification script failed to run: {e}")
            
    def test_version_import(self):
        """Test that version can be imported correctly"""
        try:
            from aws_super_cli import __version__
            self.assertIsInstance(__version__, str)
            self.assertRegex(__version__, r'^\d+\.\d+\.\d+$', 
                           "Version should be in X.Y.Z format")
        except ImportError:
            self.fail("Could not import version from aws_super_cli")

if __name__ == '__main__':
    unittest.main() 