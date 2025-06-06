"""Test cases for audit consistency bug fix (Issue #1)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from aws_super_cli.services.audit import run_security_audit, SecurityFinding


class TestAuditConsistency:
    """Test cases for audit consistency between general and service-specific audits"""
    
    @pytest.mark.asyncio
    async def test_single_account_network_audit_consistency(self):
        """Test that network audit returns same results in general vs service-specific audit"""
        
        # Mock findings that would be returned by network audit
        mock_network_findings = [
            SecurityFinding(
                resource_type='EC2',
                resource_id='sg-123456',
                finding_type='SSH_OPEN_TO_WORLD',
                severity='HIGH',
                description='Security group allows SSH from anywhere',
                region='us-east-1',
                remediation='Restrict SSH access'
            )
        ]
        
        with patch('aws_super_cli.services.audit.audit_network_security') as mock_network_audit:
            mock_network_audit.return_value = mock_network_findings
            
            # Test general audit with network service
            general_findings = await run_security_audit(
                services=['network'],
                regions=['us-east-1'],
                all_regions=False,
                profiles=None  # Single account
            )
            
            # Test service-specific audit 
            specific_findings = await run_security_audit(
                services=['network'],
                regions=['us-east-1'],
                all_regions=False,
                profiles=None  # Single account
            )
            
            # Both should return the same findings
            assert len(general_findings) == len(specific_findings)
            assert len(general_findings) == 1
            assert general_findings[0].finding_type == 'SSH_OPEN_TO_WORLD'
            assert specific_findings[0].finding_type == 'SSH_OPEN_TO_WORLD'
            
            # Verify network audit was called with correct parameters both times
            assert mock_network_audit.call_count == 2
            calls = mock_network_audit.call_args_list
            
            # Both calls should have same parameters (single account mode)
            # Check positional arguments (regions, all_regions, account)
            assert calls[0][0] == calls[1][0]  # Same positional args
            # Check that the account parameter (3rd positional arg) is None for single account
            if len(calls[0][0]) >= 3:
                assert calls[0][0][2] is None  # account parameter is None
            
    @pytest.mark.asyncio
    async def test_multi_account_profile_parameter_passed(self):
        """Test that profile parameter is correctly passed to audit functions"""
        
        test_profiles = ['profile1', 'profile2']
        
        with patch('aws_super_cli.services.audit.audit_network_security') as mock_network_audit:
            mock_network_audit.return_value = []  # No findings
            
            # Test multi-account audit
            await run_security_audit(
                services=['network'],
                regions=['us-east-1'],
                all_regions=False,
                profiles=test_profiles
            )
            
            # Should be called once per profile
            assert mock_network_audit.call_count == 2
            calls = mock_network_audit.call_args_list
            
            # Check that different profiles were passed as the account parameter
            # The account parameter should be the 3rd positional argument
            if len(calls[0][0]) >= 3:
                assert calls[0][0][2] == 'profile1'  # First call with profile1
            if len(calls[1][0]) >= 3:
                assert calls[1][0][2] == 'profile2'  # Second call with profile2
            
    @pytest.mark.asyncio
    async def test_account_field_set_in_findings(self):
        """Test that account field is properly set in findings for multi-account audit"""
        
        mock_finding = SecurityFinding(
            resource_type='S3',
            resource_id='test-bucket',
            finding_type='NO_ENCRYPTION',
            severity='HIGH',
            description='Bucket not encrypted',
            region='us-east-1',
            remediation='Enable encryption'
        )
        
        test_profile = 'test-profile'
        
        with patch('aws_super_cli.services.audit.audit_s3_buckets') as mock_s3_audit:
            mock_s3_audit.return_value = [mock_finding]
            
            # Test multi-account audit
            findings = await run_security_audit(
                services=['s3'],
                regions=['us-east-1'],
                all_regions=False,
                profiles=[test_profile]
            )
            
            # Should have one finding with account field set
            assert len(findings) == 1
            assert findings[0].account == test_profile
            
    @pytest.mark.asyncio
    async def test_no_account_field_for_single_account(self):
        """Test that account field is not set for single account audit"""
        
        mock_finding = SecurityFinding(
            resource_type='S3',
            resource_id='test-bucket',
            finding_type='NO_ENCRYPTION',
            severity='HIGH',
            description='Bucket not encrypted',
            region='us-east-1',
            remediation='Enable encryption'
        )
        
        with patch('aws_super_cli.services.audit.audit_s3_buckets') as mock_s3_audit:
            mock_s3_audit.return_value = [mock_finding]
            
            # Test single account audit
            findings = await run_security_audit(
                services=['s3'],
                regions=['us-east-1'],
                all_regions=False,
                profiles=None  # Single account
            )
            
            # Should have one finding with no account field (None)
            assert len(findings) == 1
            assert findings[0].account is None 