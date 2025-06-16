#!/usr/bin/env python3
"""
Version Consistency Verification Script
Ensures all version references are consistent across the codebase before release
"""

import sys
import os
import re
import subprocess
import tempfile
from pathlib import Path

def get_setup_py_version():
    """Extract version from setup.py"""
    setup_py_path = Path("setup.py")
    if not setup_py_path.exists():
        return None
    
    content = setup_py_path.read_text()
    match = re.search(r'version="([^"]+)"', content)
    return match.group(1) if match else None

def get_init_py_version():
    """Extract version from aws_super_cli/__init__.py"""
    init_py_path = Path("aws_super_cli/__init__.py")
    if not init_py_path.exists():
        return None
    
    content = init_py_path.read_text()
    match = re.search(r'__version__ = "([^"]+)"', content)
    return match.group(1) if match else None

def test_cli_version():
    """Test that CLI version command works and returns expected version"""
    try:
        result = subprocess.run([
            sys.executable, "-c", 
            "from aws_super_cli import __version__; print(__version__)"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception:
        return None

def test_report_version():
    """Test that generated reports show correct version"""
    try:
        # Create a temporary test to verify report version
        test_code = '''
import tempfile
import os
from aws_super_cli.services.enhanced_reporting import EnhancedSecurityReporter
from aws_super_cli.services.audit import SecurityFinding
from aws_super_cli import __version__

# Create test finding
finding = SecurityFinding(
    resource_type="S3",
    resource_id="test-bucket",
    finding_type="PUBLIC_ACL",
    severity="HIGH",
    description="Test finding",
    remediation="Test remediation",
    region="us-east-1"
)

# Generate report
reporter = EnhancedSecurityReporter()
with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
    reporter.export_enhanced_html_report([finding], f.name)
    
    # Check report contains correct version
    with open(f.name, 'r') as rf:
        content = rf.read()
        if f'v{__version__}' in content:
            print(__version__)
        else:
            print("VERSION_NOT_FOUND")
    
    os.unlink(f.name)
'''
        
        result = subprocess.run([
            sys.executable, "-c", test_code
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception:
        return None

def find_hardcoded_versions():
    """Find any hardcoded version references in the codebase"""
    hardcoded_versions = []
    
    # Pattern to find version-like strings (e.g., "0.14.1", "v0.14.1")
    version_pattern = re.compile(r'["\']v?(\d+\.\d+\.\d+)["\']')
    
    # Files to check (excluding __init__.py and setup.py which are expected)
    exclude_files = {
        "aws_super_cli/__init__.py",
        "setup.py",
        "scripts/verify_version_consistency.py"
    }
    
    for py_file in Path(".").rglob("*.py"):
        if str(py_file) in exclude_files:
            continue
            
        try:
            content = py_file.read_text()
            matches = version_pattern.findall(content)
            
            for match in matches:
                # Skip if it looks like an example or comment
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if match in line:
                        # Check if it's in a comment or docstring
                        line_stripped = line.strip()
                        if (line_stripped.startswith('#') or 
                            '"""' in line or "'''" in line or
                            'example' in line.lower() or
                            'test' in str(py_file).lower()):
                            continue
                        
                        hardcoded_versions.append({
                            'file': str(py_file),
                            'line': i,
                            'version': match,
                            'content': line.strip()
                        })
        except Exception:
            continue
    
    return hardcoded_versions

def run_version_verification():
    """Run complete version verification"""
    print("🔍 Running Version Consistency Verification...")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # 1. Check setup.py version
    setup_version = get_setup_py_version()
    if setup_version:
        print(f"✅ setup.py version: {setup_version}")
    else:
        errors.append("❌ Could not extract version from setup.py")
    
    # 2. Check __init__.py version
    init_version = get_init_py_version()
    if init_version:
        print(f"✅ __init__.py version: {init_version}")
    else:
        errors.append("❌ Could not extract version from aws_super_cli/__init__.py")
    
    # 3. Check versions match
    if setup_version and init_version:
        if setup_version == init_version:
            print(f"✅ Version consistency: {setup_version}")
        else:
            errors.append(f"❌ Version mismatch: setup.py={setup_version}, __init__.py={init_version}")
    
    # 4. Test CLI version command
    cli_version = test_cli_version()
    if cli_version:
        if cli_version == init_version:
            print(f"✅ CLI version command: {cli_version}")
        else:
            errors.append(f"❌ CLI version mismatch: expected={init_version}, got={cli_version}")
    else:
        errors.append("❌ CLI version command failed")
    
    # 5. Test report version
    report_version = test_report_version()
    if report_version and report_version != "VERSION_NOT_FOUND":
        if report_version == init_version:
            print(f"✅ Report version: {report_version}")
        else:
            errors.append(f"❌ Report version mismatch: expected={init_version}, got={report_version}")
    elif report_version == "VERSION_NOT_FOUND":
        errors.append("❌ Version not found in generated reports")
    else:
        errors.append("❌ Report version test failed")
    
    # 6. Check for hardcoded versions
    hardcoded = find_hardcoded_versions()
    if hardcoded:
        warnings.append(f"⚠️  Found {len(hardcoded)} potential hardcoded versions:")
        for hc in hardcoded:
            warnings.append(f"   {hc['file']}:{hc['line']} - {hc['content']}")
    else:
        print("✅ No hardcoded versions found")
    
    print("\n" + "=" * 50)
    
    # Summary
    if errors:
        print("❌ VERSION VERIFICATION FAILED")
        for error in errors:
            print(error)
        print("\n🔧 Fix these issues before releasing!")
        return False
    else:
        print("✅ VERSION VERIFICATION PASSED")
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings:
                print(warning)
        print(f"\n🎉 All versions consistent: {init_version}")
        return True

if __name__ == "__main__":
    # Change to script directory to ensure relative paths work
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    success = run_version_verification()
    sys.exit(0 if success else 1) 