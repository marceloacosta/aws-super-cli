import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from aws_super_cli.services.audit import (
    SecurityFinding, 
    audit_s3_buckets, 
    audit_iam_users, 
    audit_iam_policies,
    audit_guardduty_findings,
    run_security_audit, 
    get_security_summary,
    _calculate_enhanced_security_score
)


class TestGuardDutyAudit:
    """Tests for GuardDuty audit functionality"""
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_no_detectors(self):
        """Test audit when no GuardDuty detectors exist"""
        
        # Mock GuardDuty client that returns no detectors
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.return_value = {'DetectorIds': []}
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find one finding about missing detector
            assert len(findings) == 1
            assert findings[0].finding_type == 'NO_GUARDDUTY_DETECTOR'
            assert findings[0].severity == 'HIGH'
            assert 'us-east-1' in findings[0].description
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_disabled_detector(self):
        """Test audit when GuardDuty detector is disabled"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.return_value = {'DetectorIds': ['test-detector-123']}
            mock_client.get_detector.return_value = {'Status': 'DISABLED'}
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find one finding about disabled detector
            assert len(findings) == 1
            assert findings[0].finding_type == 'GUARDDUTY_DETECTOR_DISABLED'
            assert findings[0].severity == 'HIGH'
            assert 'test-detector-123' in findings[0].description
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_no_recent_threats(self):
        """Test audit when GuardDuty is enabled but no recent threats"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.return_value = {'DetectorIds': ['test-detector-123']}
            mock_client.get_detector.return_value = {'Status': 'ENABLED'}
            mock_client.list_findings.return_value = {'FindingIds': []}
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find one finding about no recent threats (which is good)
            assert len(findings) == 1
            assert findings[0].finding_type == 'NO_RECENT_THREATS'
            assert findings[0].severity == 'LOW'
            assert 'no threats' in findings[0].description.lower()
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_with_findings(self):
        """Test audit when GuardDuty has security findings"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.return_value = {'DetectorIds': ['test-detector-123']}
            mock_client.get_detector.return_value = {'Status': 'ENABLED'}
            mock_client.list_findings.return_value = {'FindingIds': ['finding-1', 'finding-2']}
            
            # Mock detailed findings response
            mock_client.get_findings.return_value = {
                'Findings': [
                    {
                        'Type': 'UnauthorizedAPICall',
                        'Severity': 8.5,
                        'Description': 'Suspicious API call detected',
                        'Resource': {
                            'ResourceType': 'Instance',
                            'InstanceDetails': {
                                'InstanceId': 'i-123456789'
                            }
                        }
                    },
                    {
                        'Type': 'Trojan:EC2/DNSDataExfiltration',
                        'Severity': 5.0,
                        'Description': 'DNS data exfiltration detected',
                        'Resource': {
                            'ResourceType': 'Instance',
                            'InstanceDetails': {
                                'InstanceId': 'i-987654321'
                            }
                        }
                    }
                ]
            }
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find two security findings
            assert len(findings) == 2
            
            # Check first finding (high severity)
            high_finding = [f for f in findings if f.severity == 'HIGH'][0]
            assert high_finding.finding_type == 'UnauthorizedAPICall'
            assert 'i-123456789' in high_finding.resource_id
            assert 'Suspicious API call' in high_finding.description
            
            # Check second finding (medium severity)
            medium_finding = [f for f in findings if f.severity == 'MEDIUM'][0]
            assert medium_finding.finding_type == 'Trojan:EC2/DNSDataExfiltration'
            assert 'i-987654321' in medium_finding.resource_id
            assert 'DNS data exfiltration' in medium_finding.description
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_s3_bucket_finding(self):
        """Test audit with S3 bucket GuardDuty finding"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.return_value = {'DetectorIds': ['test-detector-123']}
            mock_client.get_detector.return_value = {'Status': 'ENABLED'}
            mock_client.list_findings.return_value = {'FindingIds': ['s3-finding-1']}
            
            # Mock S3 finding
            mock_client.get_findings.return_value = {
                'Findings': [
                    {
                        'Type': 'S3BucketCompromised',
                        'Severity': 7.5,
                        'Description': 'S3 bucket potentially compromised',
                        'Resource': {
                            'ResourceType': 'S3Bucket',
                            'S3BucketDetails': [
                                {
                                    'Name': 'my-test-bucket'
                                }
                            ]
                        }
                    }
                ]
            }
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find one S3 finding
            assert len(findings) == 1
            assert findings[0].finding_type == 'S3BucketCompromised'
            assert findings[0].severity == 'HIGH'
            assert findings[0].resource_id == 'my-test-bucket'
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_access_key_finding(self):
        """Test audit with access key GuardDuty finding"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.return_value = {'DetectorIds': ['test-detector-123']}
            mock_client.get_detector.return_value = {'Status': 'ENABLED'}
            mock_client.list_findings.return_value = {'FindingIds': ['iam-finding-1']}
            
            # Mock IAM access key finding
            mock_client.get_findings.return_value = {
                'Findings': [
                    {
                        'Type': 'UnauthorizedAPICall:IAMUser/InstanceCredentialsExfiltration',
                        'Severity': 6.0,
                        'Description': 'Compromised IAM credentials detected',
                        'Resource': {
                            'ResourceType': 'AccessKey',
                            'AccessKeyDetails': {
                                'AccessKeyId': 'AKIA123456789EXAMPLE'
                            }
                        }
                    }
                ]
            }
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find one IAM finding
            assert len(findings) == 1
            assert findings[0].finding_type == 'UnauthorizedAPICall:IAMUser/InstanceCredentialsExfiltration'
            assert findings[0].severity == 'MEDIUM'
            assert findings[0].resource_id == 'AKIA123456789EXAMPLE'
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_error_handling(self):
        """Test audit with GuardDuty access errors"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_client.list_detectors.side_effect = Exception("Access denied")
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1'], all_regions=False)
            
            # Should find error finding
            assert len(findings) == 1
            assert findings[0].finding_type == 'GUARDDUTY_REGION_ERROR'
            assert findings[0].severity == 'MEDIUM'
            assert 'Access denied' in findings[0].description
    
    @pytest.mark.asyncio
    async def test_audit_guardduty_multiple_regions(self):
        """Test audit across multiple regions"""
        
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            
            def mock_list_detectors(*args, **kwargs):
                # Different responses for different regions
                if 'us-east-1' in str(mock_client.list_detectors.call_args):
                    return {'DetectorIds': ['detector-us-east-1']}
                else:
                    return {'DetectorIds': []}
            
            mock_client.list_detectors.side_effect = mock_list_detectors
            mock_client.get_detector.return_value = {'Status': 'ENABLED'}
            mock_client.list_findings.return_value = {'FindingIds': []}
            
            mock_session.return_value.client.return_value.__aenter__.return_value = mock_client
            
            findings = await audit_guardduty_findings(regions=['us-east-1', 'us-west-2'], all_regions=False)
            
            # Should find findings for both regions
            assert len(findings) >= 2
            regions_found = [f.region for f in findings]
            assert 'us-east-1' in regions_found
            assert 'us-west-2' in regions_found
    
    def test_security_scoring_with_guardduty(self):
        """Test security scoring includes GuardDuty findings appropriately"""
        
        findings = [
            SecurityFinding('GuardDuty', 'detector-1', 'NO_GUARDDUTY_DETECTOR', 'HIGH', 'No detector', 'us-east-1'),
            SecurityFinding('GuardDuty', 'detector-2', 'GUARDDUTY_DETECTOR_DISABLED', 'HIGH', 'Disabled', 'us-west-2'),
            SecurityFinding('GuardDuty', 'detector-3', 'NO_RECENT_THREATS', 'LOW', 'No threats', 'eu-west-1'),
            SecurityFinding('GuardDuty-Instance', 'i-123', 'UnauthorizedAPICall', 'HIGH', 'Threat detected', 'us-east-1'),
        ]
        
        score = _calculate_enhanced_security_score(findings)
        
        # Score should be significantly reduced due to critical GuardDuty issues
        assert score < 70  # Should be in the problematic range
        assert isinstance(score, int)
        assert 0 <= score <= 100
    
    @pytest.mark.asyncio
    async def test_run_security_audit_includes_guardduty(self):
        """Test that run_security_audit includes GuardDuty by default"""
        
        with patch('aws_super_cli.services.audit.audit_s3_buckets') as mock_s3, \
             patch('aws_super_cli.services.audit.audit_iam_users') as mock_iam_users, \
             patch('aws_super_cli.services.audit.audit_iam_policies') as mock_iam_policies, \
             patch('aws_super_cli.services.audit.audit_network_security') as mock_network, \
             patch('aws_super_cli.services.audit.audit_compute_security') as mock_compute, \
             patch('aws_super_cli.services.audit.audit_guardduty_findings') as mock_guardduty:
            
            # Mock all audit functions to return empty lists
            mock_s3.return_value = []
            mock_iam_users.return_value = []
            mock_iam_policies.return_value = []
            mock_network.return_value = []
            mock_compute.return_value = []
            mock_guardduty.return_value = []
            
            # Run audit with default services (should include guardduty)
            findings = await run_security_audit()
            
            # Verify GuardDuty audit was called
            mock_guardduty.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_security_audit_guardduty_only(self):
        """Test running audit with only GuardDuty service"""
        
        with patch('aws_super_cli.services.audit.audit_s3_buckets') as mock_s3, \
             patch('aws_super_cli.services.audit.audit_iam_users') as mock_iam_users, \
             patch('aws_super_cli.services.audit.audit_iam_policies') as mock_iam_policies, \
             patch('aws_super_cli.services.audit.audit_network_security') as mock_network, \
             patch('aws_super_cli.services.audit.audit_compute_security') as mock_compute, \
             patch('aws_super_cli.services.audit.audit_guardduty_findings') as mock_guardduty:
            
            # Mock GuardDuty audit to return findings
            mock_guardduty.return_value = [
                SecurityFinding('GuardDuty', 'detector-1', 'NO_RECENT_THREATS', 'LOW', 'No threats', 'us-east-1')
            ]
            
            # Run audit with only GuardDuty
            findings = await run_security_audit(services=['guardduty'])
            
            # Verify only GuardDuty audit was called
            mock_guardduty.assert_called_once()
            mock_s3.assert_not_called()
            mock_iam_users.assert_not_called()
            mock_iam_policies.assert_not_called()
            mock_network.assert_not_called()
            mock_compute.assert_not_called()
            
            # Should have GuardDuty findings
            assert len(findings) == 1
            assert findings[0].resource_type == 'GuardDuty' 