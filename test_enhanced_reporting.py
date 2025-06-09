#!/usr/bin/env python3
"""
Test script for enhanced reporting functionality
"""

import os
from aws_super_cli.services.enhanced_reporting import EnhancedSecurityReporter
from aws_super_cli.services.audit import SecurityFinding

def create_sample_findings():
    """Create sample security findings for testing"""
    return [
        SecurityFinding(
            resource_type="S3",
            resource_id="my-test-bucket",
            finding_type="PUBLIC_ACL",
            severity="HIGH",
            description="S3 bucket has public read access enabled",
            region="us-east-1",
            account="123456789012",
            remediation="Remove public ACL and enable bucket public access block"
        ),
        SecurityFinding(
            resource_type="EC2",
            resource_id="i-1234567890abcdef0",
            finding_type="SSH_OPEN_TO_WORLD",
            severity="HIGH",
            description="Security group allows SSH access from 0.0.0.0/0",
            region="us-west-2",
            account="123456789012",
            remediation="Restrict SSH access to specific IP ranges"
        ),
        SecurityFinding(
            resource_type="IAM",
            resource_id="test-user",
            finding_type="NO_MFA",
            severity="MEDIUM",
            description="IAM user does not have MFA enabled",
            region="global",
            account="123456789012",
            remediation="Enable MFA for this IAM user"
        ),
        SecurityFinding(
            resource_type="S3",
            resource_id="another-bucket",
            finding_type="NO_ENCRYPTION",
            severity="MEDIUM",
            description="S3 bucket does not have encryption enabled",
            region="us-east-1",
            account="123456789012",
            remediation="Enable server-side encryption for the bucket"
        ),
        SecurityFinding(
            resource_type="VPC",
            resource_id="vpc-1234567890abcdef0",
            finding_type="NO_FLOW_LOGS",
            severity="LOW",
            description="VPC does not have flow logs enabled",
            region="us-west-2",
            account="123456789012",
            remediation="Enable VPC flow logs for network monitoring"
        )
    ]

def test_enhanced_reporting():
    """Test the enhanced reporting functionality"""
    print("🧪 Testing Enhanced Security Reporting...")
    
    # Create sample findings
    findings = create_sample_findings()
    print(f"✓ Created {len(findings)} sample security findings")
    
    # Initialize the enhanced reporter
    reporter = EnhancedSecurityReporter()
    print("✓ Initialized EnhancedSecurityReporter")
    
    # Test executive summary generation
    print("\n📊 Testing Executive Summary Generation...")
    executive_summary = reporter.generate_executive_summary(findings)
    
    print(f"✓ Overall Score: {executive_summary.overall_score}/100")
    print(f"✓ Risk Rating: {executive_summary.risk_rating}")
    print(f"✓ Total Findings: {executive_summary.total_findings}")
    print(f"✓ Critical Issues: {executive_summary.critical_issues}")
    print(f"✓ High Priority Actions: {len(executive_summary.high_priority_actions)}")
    print(f"✓ Key Metrics: {executive_summary.key_metrics}")
    print(f"✓ Recommendations: {len(executive_summary.recommendations)}")
    print(f"✓ Compliance Status: {executive_summary.compliance_status}")
    
    # Test enhanced HTML export
    print("\n📄 Testing Enhanced HTML Report Export...")
    output_file = "test_enhanced_report.html"
    
    try:
        reporter.export_enhanced_html_report(findings, output_file, show_account=True)
        print(f"✓ Enhanced HTML report exported to: {output_file}")
        
        # Verify file was created and has content
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✓ Report file size: {file_size:,} bytes")
            
            # Read a sample of the content to verify it's HTML
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('<!DOCTYPE html'):
                    print("✓ File contains valid HTML content")
                    
                    # Check for key sections
                    if "Executive Summary" in content:
                        print("✓ Executive Summary section present")
                    if "Security Metrics Dashboard" in content:
                        print("✓ Metrics Dashboard section present")
                    if "Detailed Security Findings" in content:
                        print("✓ Detailed Findings section present")
                    if "Immediate Action Items" in content:
                        print("✓ Action Items section present")
                else:
                    print("❌ File does not contain valid HTML")
        else:
            print("❌ Report file was not created")
            
    except Exception as e:
        print(f"❌ Error exporting enhanced HTML report: {e}")
        return False
    
    print("\n🎉 Enhanced Reporting Test Completed Successfully!")
    print(f"\nGenerated Files:")
    print(f"  - {output_file}")
    
    return True

if __name__ == "__main__":
    success = test_enhanced_reporting()
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        exit(1) 