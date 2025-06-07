"""Test cases for audit export functionality (Issue #3)"""

import pytest
import tempfile
import os
import csv
from aws_super_cli.services.audit import (
    SecurityFinding, 
    export_findings_csv, 
    export_findings_txt, 
    export_findings_html
)


class TestAuditExport:
    """Test audit export functionality"""
    
    @pytest.fixture
    def sample_findings(self):
        """Create sample security findings for testing"""
        return [
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
            ),
            SecurityFinding(
                resource_type="S3",
                resource_id="test-bucket-2",
                finding_type="NO_ENCRYPTION",
                severity="LOW",
                description="S3 bucket does not have default encryption enabled",
                region="us-east-1",
                account="prod-account",
                remediation="Enable default encryption for S3 bucket"
            )
        ]
    
    def test_csv_export_basic(self, sample_findings):
        """Test basic CSV export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_csv(sample_findings, filepath, show_account=False)
            
            # Verify file was created
            assert os.path.exists(filepath)
            
            # Read and verify CSV content
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                # Check header
                expected_headers = ['severity', 'service', 'resource', 'finding_type', 'description', 'region', 'remediation']
                assert reader.fieldnames == expected_headers
                
                # Check number of rows
                assert len(rows) == 4
                
                # Check content (should be sorted by severity)
                assert rows[0]['severity'] == 'HIGH'
                assert rows[0]['service'] == 'S3'
                assert rows[0]['resource'] == 'test-bucket-1'
                
                assert rows[1]['severity'] == 'HIGH'
                assert rows[1]['service'] == 'EC2'
                
                assert rows[2]['severity'] == 'MEDIUM'
                assert rows[2]['service'] == 'IAM'
                
                assert rows[3]['severity'] == 'LOW'
                
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_csv_export_with_accounts(self, sample_findings):
        """Test CSV export with account column"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_csv(sample_findings, filepath, show_account=True)
            
            # Read and verify CSV content
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                # Check header includes account
                expected_headers = ['account', 'severity', 'service', 'resource', 'finding_type', 'description', 'region', 'remediation']
                assert reader.fieldnames == expected_headers
                
                # Check account values
                assert rows[0]['account'] == 'test-account'
                assert rows[3]['account'] == 'prod-account'
                
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_txt_export_basic(self, sample_findings):
        """Test basic TXT export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_txt(sample_findings, filepath, show_account=False)
            
            # Verify file was created
            assert os.path.exists(filepath)
            
            # Read and verify TXT content
            with open(filepath, 'r', encoding='utf-8') as txtfile:
                content = txtfile.read()
                
                # Check header
                assert "AWS SUPER CLI - SECURITY AUDIT REPORT" in content
                assert "Total Findings: 4" in content
                
                # Check summary
                assert "High Risk:   2" in content
                assert "Medium Risk: 1" in content
                assert "Low Risk:    1" in content
                
                # Check services breakdown
                assert "S3: 2" in content
                assert "IAM: 1" in content
                assert "EC2: 1" in content
                
                # Check detailed findings
                assert "Finding #1" in content
                assert "Severity:    HIGH" in content
                assert "test-bucket-1" in content
                assert "PUBLIC_READ_ACCESS" in content
                
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_txt_export_with_accounts(self, sample_findings):
        """Test TXT export with account information"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_txt(sample_findings, filepath, show_account=True)
            
            # Read and verify TXT content
            with open(filepath, 'r', encoding='utf-8') as txtfile:
                content = txtfile.read()
                
                # Check account information is included
                assert "Account:     test-account" in content
                assert "Account:     prod-account" in content
                
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_html_export_basic(self, sample_findings):
        """Test basic HTML export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_html(sample_findings, filepath, show_account=False)
            
            # Verify file was created
            assert os.path.exists(filepath)
            
            # Read and verify HTML content
            with open(filepath, 'r', encoding='utf-8') as htmlfile:
                content = htmlfile.read()
                
                # Check HTML structure
                assert "<!DOCTYPE html>" in content
                assert "<title>AWS Security Audit Report</title>" in content
                assert "Total Findings: 4" in content
                
                # Check summary cards
                assert "Security Score" in content
                assert "High Risk" in content
                assert "Medium Risk" in content
                assert "Low Risk" in content
                
                # Check services breakdown
                assert "service-name" in content
                assert "service-count" in content
                
                # Check findings table
                assert "findings-table" in content
                assert "test-bucket-1" in content
                assert "PUBLIC_READ_ACCESS" in content
                assert "severity-high" in content
                
                # Check CSS styling
                assert ".severity-high { color: #e74c3c;" in content
                assert ".severity-medium { color: #f39c12;" in content
                assert ".severity-low { color: #27ae60;" in content
                
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_html_export_with_accounts(self, sample_findings):
        """Test HTML export with account column"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_html(sample_findings, filepath, show_account=True)
            
            # Read and verify HTML content
            with open(filepath, 'r', encoding='utf-8') as htmlfile:
                content = htmlfile.read()
                
                # Check account header and values
                assert "<th>Account</th>" in content
                assert "<td>test-account</td>" in content
                assert "<td>prod-account</td>" in content
                
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
    
    def test_empty_findings_export(self):
        """Test export with empty findings list"""
        findings = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            txt_path = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            html_path = f.name
        
        try:
            # Test CSV export with empty findings
            export_findings_csv(findings, csv_path)
            assert os.path.exists(csv_path)
            
            with open(csv_path, 'r') as f:
                content = f.read()
                assert "severity,service,resource" in content  # Header should still be there
            
            # Test TXT export with empty findings
            export_findings_txt(findings, txt_path)
            assert os.path.exists(txt_path)
            
            with open(txt_path, 'r') as f:
                content = f.read()
                assert "Total Findings: 0" in content
            
            # Test HTML export with empty findings
            export_findings_html(findings, html_path)
            assert os.path.exists(html_path)
            
            with open(html_path, 'r') as f:
                content = f.read()
                assert "Total Findings: 0" in content
                assert "findings-table" in content  # Table structure should still exist
                
        finally:
            for path in [csv_path, txt_path, html_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_export_file_permissions(self, sample_findings):
        """Test that exported files can be read"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            export_findings_csv(sample_findings, filepath)
            
            # Check file is readable
            assert os.access(filepath, os.R_OK)
            
            # Check file has content
            assert os.path.getsize(filepath) > 0
            
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath) 