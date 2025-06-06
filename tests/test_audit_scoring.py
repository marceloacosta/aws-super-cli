"""Test cases for enhanced security scoring algorithm (Issue #2)"""

import pytest
from aws_super_cli.services.audit import SecurityFinding, _calculate_enhanced_security_score, get_security_summary


class TestEnhancedSecurityScoring:
    """Test the enhanced security scoring algorithm"""
    
    def test_empty_findings_returns_100(self):
        """Test that no findings results in perfect score"""
        findings = []
        summary = get_security_summary(findings)
        assert summary['score'] == 100
        assert summary['total'] == 0
    
    def test_critical_exposure_findings_major_penalty(self):
        """Test that critical exposure findings result in major score penalty"""
        findings = [
            SecurityFinding(
                resource_type='EC2',
                resource_id='sg-123',
                finding_type='SSH_OPEN_TO_WORLD',
                severity='HIGH',
                description='SSH open to world',
                region='us-east-1'
            ),
            SecurityFinding(
                resource_type='EC2',
                resource_id='sg-456',
                finding_type='RDP_OPEN_TO_WORLD',
                severity='HIGH',
                description='RDP open to world',
                region='us-east-1'
            )
        ]
        
        score = _calculate_enhanced_security_score(findings)
        # Should be significantly lower due to critical exposure
        assert 40 <= score <= 80  # Reasonable range for critical issues
    
    def test_monitoring_gaps_lighter_penalty(self):
        """Test that monitoring gaps have lighter penalty than security exposure"""
        findings = [
            SecurityFinding(
                resource_type='VPC',
                resource_id='vpc-123',
                finding_type='NO_FLOW_LOGS',
                severity='MEDIUM',
                description='No flow logs',
                region='us-east-1'
            ),
            SecurityFinding(
                resource_type='S3',
                resource_id='bucket-123',
                finding_type='NO_ACCESS_LOGGING',
                severity='MEDIUM',
                description='No access logging',
                region='us-east-1'
            )
        ]
        
        score = _calculate_enhanced_security_score(findings)
        # Monitoring gaps should result in higher score than critical exposure
        assert 80 <= score <= 95
    
    def test_operational_cleanup_minimal_penalty(self):
        """Test that operational cleanup items have minimal impact"""
        findings = [
            SecurityFinding(
                resource_type='EC2',
                resource_id='sg-unused',
                finding_type='UNUSED_SECURITY_GROUP',
                severity='LOW',
                description='Unused security group',
                region='us-east-1'
            ),
            SecurityFinding(
                resource_type='IAM',
                resource_id='old-user',
                finding_type='INACTIVE_USER',
                severity='LOW',
                description='Inactive user',
                region='global'
            )
        ]
        
        score = _calculate_enhanced_security_score(findings)
        # Cleanup items should have minimal impact
        assert 85 <= score <= 98
    
    def test_logarithmic_scaling_diminishing_returns(self):
        """Test that multiple similar findings have diminishing returns"""
        # Create many monitoring gap findings
        findings = []
        for i in range(10):
            findings.append(SecurityFinding(
                resource_type='VPC',
                resource_id=f'vpc-{i}',
                finding_type='NO_FLOW_LOGS',
                severity='MEDIUM',
                description='No flow logs',
                region='us-east-1'
            ))
        
        score = _calculate_enhanced_security_score(findings)
        
        # Even with 10 monitoring findings, score shouldn't be terrible
        # due to logarithmic scaling and capping
        assert 70 <= score <= 90
    
    def test_mixed_findings_realistic_score(self):
        """Test mixed findings scenario similar to real-world audit"""
        findings = [
            # Critical exposure (12 findings)
            *[SecurityFinding(
                resource_type='EC2',
                resource_id=f'sg-{i}',
                finding_type='SSH_OPEN_TO_WORLD',
                severity='HIGH',
                description='SSH open to world',
                region='us-east-1'
            ) for i in range(12)],
            
            # Monitoring gaps (7 findings)
            *[SecurityFinding(
                resource_type='VPC',
                resource_id=f'vpc-{i}',
                finding_type='NO_FLOW_LOGS',
                severity='MEDIUM',
                description='No flow logs',
                region='us-east-1'
            ) for i in range(7)],
            
            # Operational cleanup (11 findings)
            *[SecurityFinding(
                resource_type='EC2',
                resource_id=f'sg-unused-{i}',
                finding_type='UNUSED_SECURITY_GROUP',
                severity='LOW',
                description='Unused security group',
                region='us-east-1'
            ) for i in range(11)],
            
            # Configuration drift (rest of findings)
            *[SecurityFinding(
                resource_type='VPC',
                resource_id=f'subnet-{i}',
                finding_type='PUBLIC_SUBNET_AUTO_IP',
                severity='MEDIUM',
                description='Public subnet auto IP',
                region='us-east-1'
            ) for i in range(10)]
        ]
        
        score = _calculate_enhanced_security_score(findings)
        summary = get_security_summary(findings)
        
        # This should result in a reasonable score (30-50 range)
        # instead of 0 like the old algorithm
        assert 30 <= score <= 60
        assert summary['score'] == score
        assert summary['total'] == 40  # Total findings
    
    def test_score_never_below_10(self):
        """Test that score never goes below 10 even with many critical findings"""
        # Create excessive critical findings
        findings = []
        for i in range(50):
            findings.append(SecurityFinding(
                resource_type='S3',
                resource_id=f'bucket-{i}',
                finding_type='PUBLIC_POLICY',
                severity='HIGH',
                description='Public bucket policy',
                region='us-east-1'
            ))
        
        score = _calculate_enhanced_security_score(findings)
        assert score >= 10  # Never below 10
    
    def test_score_never_above_100(self):
        """Test that score calculation doesn't exceed 100"""
        # This should never happen with the algorithm, but let's verify
        findings = []  # Empty findings
        score = _calculate_enhanced_security_score(findings)
        assert score <= 100
    
    def test_categorization_accuracy(self):
        """Test that findings are categorized correctly"""
        findings = [
            # Should be critical_exposure
            SecurityFinding(
                resource_type='EC2',
                resource_id='sg-1',
                finding_type='SSH_OPEN_TO_WORLD',
                severity='HIGH',
                description='SSH open',
                region='us-east-1'
            ),
            # Should be encryption_gaps
            SecurityFinding(
                resource_type='S3',
                resource_id='bucket-1',
                finding_type='NO_ENCRYPTION',
                severity='HIGH',
                description='No encryption',
                region='us-east-1'
            ),
            # Should be access_control
            SecurityFinding(
                resource_type='IAM',
                resource_id='user-1',
                finding_type='ADMIN_USER',
                severity='HIGH',
                description='Admin user',
                region='global'
            ),
            # Should be monitoring_gaps
            SecurityFinding(
                resource_type='VPC',
                resource_id='vpc-1',
                finding_type='NO_FLOW_LOGS',
                severity='MEDIUM',
                description='No flow logs',
                region='us-east-1'
            ),
            # Should be operational_cleanup
            SecurityFinding(
                resource_type='EC2',
                resource_id='sg-unused',
                finding_type='UNUSED_SECURITY_GROUP',
                severity='LOW',
                description='Unused SG',
                region='us-east-1'
            )
        ]
        
        # Each category has different impact, so score should reflect this
        score = _calculate_enhanced_security_score(findings)
        
        # With one finding from each category, should be moderate penalty
        assert 50 <= score <= 80
    
    def test_real_world_scenario_comparison(self):
        """Test with findings similar to the real audit results that showed 0/100"""
        
        # Simulate the 46 findings from the real audit
        findings = [
            # 14 HIGH findings (mostly SSH open to world and subnet issues)
            *[SecurityFinding(
                resource_type='EC2',
                resource_id=f'sg-{i}',
                finding_type='SSH_OPEN_TO_WORLD',
                severity='HIGH',
                description='SSH open to world',
                region='us-east-1'
            ) for i in range(12)],
            
            *[SecurityFinding(
                resource_type='VPC',
                resource_id=f'subnet-{i}',
                finding_type='PRIVATE_SUBNET_AUTO_IP',
                severity='HIGH',
                description='Private subnet auto IP',
                region='us-east-1'
            ) for i in range(2)],
            
            # 16 MEDIUM findings (flow logs, subnet configs)
            *[SecurityFinding(
                resource_type='VPC',
                resource_id=f'vpc-{i}',
                finding_type='NO_FLOW_LOGS',
                severity='MEDIUM',
                description='No flow logs',
                region='us-east-1'
            ) for i in range(8)],
            
            *[SecurityFinding(
                resource_type='VPC',
                resource_id=f'subnet-pub-{i}',
                finding_type='PUBLIC_SUBNET_AUTO_IP',
                severity='MEDIUM',
                description='Public subnet auto IP',
                region='us-east-1'
            ) for i in range(8)],
            
            # 16 LOW findings (unused security groups, internet gateways)
            *[SecurityFinding(
                resource_type='EC2',
                resource_id=f'sg-unused-{i}',
                finding_type='UNUSED_SECURITY_GROUP',
                severity='LOW',
                description='Unused security group',
                region='us-east-1'
            ) for i in range(11)],
            
            *[SecurityFinding(
                resource_type='VPC',
                resource_id=f'vpc-igw-{i}',
                finding_type='INTERNET_GATEWAY_ATTACHED',
                severity='LOW',
                description='Internet gateway attached',
                region='us-east-1'
            ) for i in range(5)]
        ]
        
        # Old algorithm: 14*20 + 16*10 + 16*5 = 280 + 160 + 80 = 520 penalty = 0/100
        # New algorithm should give a reasonable score
        score = _calculate_enhanced_security_score(findings)
        
        # Should be in the 30-50 range instead of 0
        assert 25 <= score <= 55
        print(f"Real-world scenario score: {score}/100 (was 0/100 with old algorithm)") 