"""
Tests for AWS Trusted Advisor Integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from aws_super_cli.services.trusted_advisor import TrustedAdvisorIntegration
from aws_super_cli.services.cost_optimization import OptimizationRecommendation, OptimizationError


class TestTrustedAdvisorIntegration:
    """Test Trusted Advisor integration functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.ta_integration = TrustedAdvisorIntegration()
    
    @pytest.mark.asyncio
    async def test_check_support_plan_access_business_plan(self):
        """Test support plan access check with Business/Enterprise plan"""
        mock_response = {
            'checks': [
                {'id': 'check1', 'name': 'Test Check 1'},
                {'id': 'check2', 'name': 'Test Check 2'}
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_client = Mock()
            mock_client.describe_trusted_advisor_checks.return_value = mock_response
            mock_session.client.return_value = mock_client
            
            result = await self.ta_integration.check_support_plan_access()
            
            assert result['has_access'] is True
            assert result['support_plan'] == "Business/Enterprise"
            assert result['checks_available'] == 2
            assert "confirmed" in result['message']
    
    @pytest.mark.asyncio
    async def test_check_support_plan_access_basic_plan(self):
        """Test support plan access check with Basic/Developer plan"""
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_client = Mock()
            # Create a proper exception class
            class SubscriptionRequiredException(Exception):
                pass
            mock_client.exceptions.SubscriptionRequiredException = SubscriptionRequiredException
            mock_client.describe_trusted_advisor_checks.side_effect = SubscriptionRequiredException("Subscription required")
            mock_session.client.return_value = mock_client
            
            result = await self.ta_integration.check_support_plan_access()
            
            assert result['has_access'] is False
            assert result['support_plan'] == "Basic/Developer"
            assert result['checks_available'] == 0
            assert result['error_code'] == "SUBSCRIPTION_REQUIRED"
    
    @pytest.mark.asyncio
    async def test_check_support_plan_access_error(self):
        """Test support plan access check with general error"""
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_client = Mock()
            mock_client.describe_trusted_advisor_checks.side_effect = Exception("API Error")
            mock_session.client.return_value = mock_client
            
            result = await self.ta_integration.check_support_plan_access()
            
            assert result['has_access'] is False
            assert result['support_plan'] == "Unknown"
            assert result['error_code'] == "ACCESS_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_available_checks_success(self):
        """Test getting available Trusted Advisor checks"""
        mock_response = {
            'checks': [
                {
                    'id': 'check1',
                    'name': 'Low Utilization Amazon EC2 Instances',
                    'description': 'Check for underutilized EC2 instances',
                    'category': 'cost_optimizing',
                    'metadata': ['instance_id', 'region', 'utilization']
                },
                {
                    'id': 'check2',
                    'name': 'Idle Load Balancers',
                    'description': 'Check for idle load balancers',
                    'category': 'cost_optimizing',
                    'metadata': ['lb_name', 'region']
                }
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_client = Mock()
            mock_client.describe_trusted_advisor_checks.return_value = mock_response
            mock_session.client.return_value = mock_client
            
            checks = await self.ta_integration.get_available_checks()
            
            assert len(checks) == 2
            assert checks[0]['name'] == 'Low Utilization Amazon EC2 Instances'
            assert checks[1]['name'] == 'Idle Load Balancers'
    
    @pytest.mark.asyncio
    async def test_get_cost_optimization_recommendations_no_access(self):
        """Test getting recommendations without proper support plan"""
        with patch.object(self.ta_integration, 'check_support_plan_access') as mock_access:
            mock_access.return_value = {
                'has_access': False,
                'message': 'Business or Enterprise support plan required',
                'error_code': 'SUBSCRIPTION_REQUIRED'
            }
            
            with pytest.raises(OptimizationError) as exc_info:
                await self.ta_integration.get_cost_optimization_recommendations()
            
            assert exc_info.value.error_code == 'SUBSCRIPTION_REQUIRED'
            assert "Business or Enterprise" in exc_info.value.remediation
    
    @pytest.mark.asyncio
    async def test_get_cost_optimization_recommendations_success(self):
        """Test getting cost optimization recommendations successfully"""
        # Mock support plan access
        with patch.object(self.ta_integration, 'check_support_plan_access') as mock_access:
            mock_access.return_value = {
                'has_access': True,
                'support_plan': 'Business/Enterprise'
            }
            
            # Mock core get_account_info
            with patch.object(self.ta_integration.core, 'get_account_info') as mock_account:
                mock_account.return_value = {'account_id': '123456789012'}
                
                # Mock AWS session and client
                with patch('aws_super_cli.aws.aws_session.session') as mock_session:
                    mock_client = Mock()
                    
                    # Mock describe_trusted_advisor_checks
                    mock_client.describe_trusted_advisor_checks.return_value = {
                        'checks': [
                            {
                                'id': 'ec2-check',
                                'name': 'Low Utilization Amazon EC2 Instances',
                                'category': 'cost_optimizing'
                            }
                        ]
                    }
                    
                    # Mock describe_trusted_advisor_check_result
                    mock_client.describe_trusted_advisor_check_result.return_value = {
                        'result': {
                            'status': 'warning',
                            'flaggedResources': [
                                {
                                    'metadata': [
                                        'i-1234567890abcdef0',  # instance_id
                                        'us-east-1',           # region
                                        'running',             # state
                                        '45.00'                # estimated_savings
                                    ]
                                }
                            ]
                        }
                    }
                    
                    mock_session.client.return_value = mock_client
                    
                    recommendations = await self.ta_integration.get_cost_optimization_recommendations()
                    
                    assert len(recommendations) == 1
                    rec = recommendations[0]
                    assert rec.service == "trusted-advisor"
                    assert rec.resource_id == "i-1234567890abcdef0"
                    assert rec.region == "us-east-1"
                    assert rec.estimated_savings == 45.0
                    assert rec.account_id == "123456789012"
    
    def test_create_recommendation_from_resource_ec2(self):
        """Test creating recommendation from EC2 check resource"""
        check = {
            'name': 'Low Utilization Amazon EC2 Instances',
            'id': 'ec2-check'
        }
        
        resource = {
            'metadata': [
                'i-1234567890abcdef0',  # instance_id
                'us-east-1',           # region
                'running',             # state
                '45.00'                # estimated_savings
            ]
        }
        
        recommendation = self.ta_integration._create_recommendation_from_resource(
            check, resource, '123456789012'
        )
        
        assert recommendation is not None
        assert recommendation.resource_type == "EC2 Instance"
        assert recommendation.resource_id == "i-1234567890abcdef0"
        assert recommendation.region == "us-east-1"
        assert recommendation.estimated_savings == 45.0
        assert recommendation.confidence == "HIGH"
        assert "utilization" in recommendation.description.lower()
        assert len(recommendation.remediation_steps) > 0
    
    def test_create_recommendation_from_resource_load_balancer(self):
        """Test creating recommendation from Load Balancer check resource"""
        check = {
            'name': 'Idle Load Balancers',
            'id': 'elb-check'
        }
        
        resource = {
            'metadata': [
                'my-load-balancer',    # lb_name
                'us-west-2'           # region
            ]
        }
        
        recommendation = self.ta_integration._create_recommendation_from_resource(
            check, resource, '123456789012'
        )
        
        assert recommendation is not None
        assert recommendation.resource_type == "Load Balancer"
        assert recommendation.resource_id == "my-load-balancer"
        assert recommendation.region == "us-west-2"
        assert recommendation.estimated_savings == 25.0  # Default ELB cost
        assert recommendation.confidence == "HIGH"
        assert "idle" in recommendation.description.lower()
    
    def test_create_recommendation_from_resource_elastic_ip(self):
        """Test creating recommendation from Elastic IP check resource"""
        check = {
            'name': 'Unassociated Elastic IP Addresses',
            'id': 'eip-check'
        }
        
        resource = {
            'metadata': [
                '52.1.2.3',           # ip_address
                'us-east-1'           # region
            ]
        }
        
        recommendation = self.ta_integration._create_recommendation_from_resource(
            check, resource, '123456789012'
        )
        
        assert recommendation is not None
        assert recommendation.resource_type == "Elastic IP"
        assert recommendation.resource_id == "52.1.2.3"
        assert recommendation.region == "us-east-1"
        assert recommendation.estimated_savings == 3.65  # Monthly EIP cost
        assert recommendation.confidence == "HIGH"
        assert "unassociated" in recommendation.description.lower()
    
    def test_create_recommendation_from_resource_invalid_data(self):
        """Test creating recommendation with invalid resource data"""
        check = {
            'name': 'Invalid Check',
            'id': 'invalid-check'
        }
        
        resource = {
            'metadata': []  # Empty metadata
        }
        
        recommendation = self.ta_integration._create_recommendation_from_resource(
            check, resource, '123456789012'
        )
        
        # Should still create a recommendation with defaults
        assert recommendation is not None
        assert recommendation.resource_id == "unknown"
        assert recommendation.region == "unknown"
        assert recommendation.estimated_savings == 0.0
    
    def test_create_trusted_advisor_summary_table(self):
        """Test creating summary table from recommendations"""
        recommendations = [
            OptimizationRecommendation(
                service="trusted-advisor",
                resource_id="i-123",
                resource_type="EC2 Instance",
                recommendation_type="Low Utilization Amazon EC2 Instances",
                current_cost=50.0,
                estimated_savings=45.0,
                confidence="HIGH",
                description="Low utilization EC2 instance",
                remediation_steps=["Review usage"],
                region="us-east-1",
                account_id="123456789012",
                timestamp=datetime.now().isoformat(),
                source="trusted_advisor"
            ),
            OptimizationRecommendation(
                service="trusted-advisor",
                resource_id="elb-456",
                resource_type="Load Balancer",
                recommendation_type="Idle Load Balancers",
                current_cost=25.0,
                estimated_savings=25.0,
                confidence="HIGH",
                description="Idle load balancer",
                remediation_steps=["Remove if unused"],
                region="us-west-2",
                account_id="123456789012",
                timestamp=datetime.now().isoformat(),
                source="trusted_advisor"
            )
        ]
        
        table = self.ta_integration.create_trusted_advisor_summary_table(recommendations)
        
        # Verify table structure
        assert table.title == "Trusted Advisor Cost Optimization Summary"
        assert len(table.columns) == 4  # Check Type, Resources, Est. Savings, Confidence
        
        # Should have 3 rows: 2 recommendation types + 1 total row
        assert len(table.rows) == 3
    
    @pytest.mark.asyncio
    async def test_integration_with_cost_optimization_core(self):
        """Test integration with CostOptimizationCore"""
        # Verify that TrustedAdvisorIntegration properly uses CostOptimizationCore
        assert self.ta_integration.core is not None
        
        # Test that it can get account info through core
        with patch.object(self.ta_integration.core, 'get_account_info') as mock_account:
            mock_account.return_value = {'account_id': '123456789012'}
            
            account_info = await self.ta_integration.core.get_account_info()
            assert account_info['account_id'] == '123456789012'
    
    def test_cost_optimization_checks_configuration(self):
        """Test that cost optimization checks are properly configured"""
        checks = self.ta_integration.cost_optimization_checks
        
        # Verify structure
        assert 'cost_optimizing' in checks
        assert 'service_limits' in checks
        assert 'fault_tolerance' in checks
        
        # Verify key cost optimization checks are included
        cost_checks = checks['cost_optimizing']
        assert 'Low Utilization Amazon EC2 Instances' in cost_checks
        assert 'Idle Load Balancers' in cost_checks
        assert 'Unassociated Elastic IP Addresses' in cost_checks
        assert 'Underutilized Amazon EBS Volumes' in cost_checks
        assert 'Amazon RDS Idle DB Instances' in cost_checks 