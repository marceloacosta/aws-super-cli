#!/usr/bin/env python3
"""Direct test of export functionality"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from aws_super_cli.services.audit import (
    SecurityFinding, 
    export_findings_csv, 
    export_findings_txt, 
    export_findings_html
)

def test_export_functionality():
    """Test all export formats with sample data"""
    
    # Create sample findings
    findings = [
        SecurityFinding(
            resource_type="S3",
            resource_id="test-bucket-1", 
            finding_type="PUBLIC_READ_ACCESS",
            severity="HIGH",
            description="S3 bucket allows public read access",
            region="us-east-1",
            account="test-account",
            remediation="Remove public read permissions from bucket policy"
        ),
        SecurityFinding(
            resource_type="IAM",
            resource_id="test-user",
            finding_type="NO_MFA", 
            severity="MEDIUM",
            description="IAM user does not have MFA enabled",
            region="global",
            account="test-account",
            remediation="Enable MFA for IAM user"
        ),
        SecurityFinding(
            resource_type="EC2",
            resource_id="i-123456789",
            finding_type="UNRESTRICTED_SSH",
            severity="HIGH", 
            description="Security group allows unrestricted SSH access (0.0.0.0/0:22)",
            region="us-west-2",
            account="test-account",
            remediation="Restrict SSH access to specific IP ranges"
        )
    ]
    
    print(f"Testing export functionality with {len(findings)} sample findings...")
    
    # Test CSV export
    try:
        export_findings_csv(findings, "test_audit_export.csv", show_account=True)
        print("✓ CSV export successful: test_audit_export.csv")
        
        # Verify CSV content
        with open("test_audit_export.csv", "r") as f:
            csv_content = f.read()
            assert "severity,service,resource" in csv_content
            assert "HIGH,S3,test-bucket-1" in csv_content
            print("  ✓ CSV content verified")
            
    except Exception as e:
        print(f"✗ CSV export failed: {e}")
        return False
    
    # Test TXT export
    try:
        export_findings_txt(findings, "test_audit_export.txt", show_account=True)
        print("✓ TXT export successful: test_audit_export.txt")
        
        # Verify TXT content
        with open("test_audit_export.txt", "r") as f:
            txt_content = f.read()
            assert "AWS SUPER CLI - SECURITY AUDIT REPORT" in txt_content
            assert "Total Findings: 3" in txt_content
            assert "High Risk:   2" in txt_content
            print("  ✓ TXT content verified")
            
    except Exception as e:
        print(f"✗ TXT export failed: {e}")
        return False
    
    # Test HTML export
    try:
        export_findings_html(findings, "test_audit_export.html", show_account=True)
        print("✓ HTML export successful: test_audit_export.html")
        
        # Verify HTML content
        with open("test_audit_export.html", "r") as f:
            html_content = f.read()
            assert "<!DOCTYPE html>" in html_content
            assert "AWS Security Audit Report" in html_content
            assert "Total Findings: 3" in html_content
            assert "test-bucket-1" in html_content
            print("  ✓ HTML content verified")
            
    except Exception as e:
        print(f"✗ HTML export failed: {e}")
        return False
    
    print("\n✅ All export formats working correctly!")
    print("\nGenerated files:")
    print("  - test_audit_export.csv")
    print("  - test_audit_export.txt") 
    print("  - test_audit_export.html")
    
    return True

if __name__ == "__main__":
    success = test_export_functionality()
    sys.exit(0 if success else 1) 