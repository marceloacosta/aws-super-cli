"""
Tests for AWS Compute Optimizer Integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from aws_super_cli.services.compute_optimizer import ComputeOptimizerIntegration
from aws_super_cli.services.cost_optimization import OptimizationRecommendation, OptimizationError


@pytest.fixture
def compute_optimizer():
    """Create ComputeOptimizerIntegration instance for testing"""
    return ComputeOptimizerIntegration()


@pytest.fixture
def mock_compute_optimizer_client():
    """Mock Compute Optimizer client"""
    client = Mock()
    return client


class TestComputeOptimizerIntegration:
    """Test Compute Optimizer integration functionality"""
    
    @pytest.mark.asyncio
    async def test_check_enrollment_status_active(self, compute_optimizer, mock_compute_optimizer_client):
        """Test checking enrollment status when active"""
        # Mock response for active enrollment
        mock_compute_optimizer_client.get_enrollment_status.return_value = {
            'status': 'Active',
            'statusReason': 'Account is enrolled',
            'memberAccountsEnrolled': True
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            result = await compute_optimizer.check_enrollment_status()
            
            assert result['enrolled'] is True
            assert result['status'] == 'Active'
            assert result['member_accounts_enrolled'] is True
            assert 'Compute Optimizer status: Active' in result['message']
    
    @pytest.mark.asyncio
    async def test_check_enrollment_status_inactive(self, compute_optimizer, mock_compute_optimizer_client):
        """Test checking enrollment status when inactive"""
        # Mock response for inactive enrollment
        mock_compute_optimizer_client.get_enrollment_status.return_value = {
            'status': 'Inactive',
            'statusReason': 'Account is not enrolled',
            'memberAccountsEnrolled': False
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            result = await compute_optimizer.check_enrollment_status()
            
            assert result['enrolled'] is False
            assert result['status'] == 'Inactive'
            assert result['member_accounts_enrolled'] is False
    
    @pytest.mark.asyncio
    async def test_check_enrollment_status_access_denied(self, compute_optimizer, mock_compute_optimizer_client):
        """Test checking enrollment status with access denied"""
        # Mock access denied error
        mock_compute_optimizer_client.get_enrollment_status.side_effect = Exception('AccessDenied')
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            result = await compute_optimizer.check_enrollment_status()
            
            assert result['enrolled'] is False
            assert result['status'] == 'Permission Denied'
            assert result['error_code'] == 'ACCESS_DENIED'
            assert 'ComputeOptimizerReadOnlyAccess IAM policy required' in result['message']
    
    @pytest.mark.asyncio
    async def test_activate_enrollment_success(self, compute_optimizer, mock_compute_optimizer_client):
        """Test successful enrollment activation"""
        # Mock inactive status first, then successful activation
        mock_compute_optimizer_client.get_enrollment_status.return_value = {
            'status': 'Inactive',
            'statusReason': 'Account is not enrolled',
            'memberAccountsEnrolled': False
        }
        mock_compute_optimizer_client.update_enrollment_status.return_value = {
            'status': 'Active'
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            result = await compute_optimizer.activate_enrollment()
            
            assert result['success'] is True
            assert result['action'] == 'activated'
            assert 'enrollment activated successfully' in result['message']
    
    @pytest.mark.asyncio
    async def test_activate_enrollment_already_active(self, compute_optimizer, mock_compute_optimizer_client):
        """Test activation when already enrolled"""
        # Mock active status
        mock_compute_optimizer_client.get_enrollment_status.return_value = {
            'status': 'Active',
            'statusReason': 'Account is enrolled',
            'memberAccountsEnrolled': True
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            result = await compute_optimizer.activate_enrollment()
            
            assert result['success'] is True
            assert result['action'] == 'none'
            assert 'already enrolled' in result['message']
    
    @pytest.mark.asyncio
    async def test_activate_enrollment_access_denied(self, compute_optimizer, mock_compute_optimizer_client):
        """Test activation with access denied"""
        # Mock inactive status first, then access denied on activation
        mock_compute_optimizer_client.get_enrollment_status.return_value = {
            'status': 'Inactive',
            'statusReason': 'Account is not enrolled',
            'memberAccountsEnrolled': False
        }
        mock_compute_optimizer_client.update_enrollment_status.side_effect = Exception('AccessDenied')
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            result = await compute_optimizer.activate_enrollment()
            
            assert result['success'] is False
            assert result['action'] == 'failed'
            assert result['error_code'] == 'ACCESS_DENIED'
            assert 'ComputeOptimizerFullAccess' in result['message']
    
    @pytest.mark.asyncio
    async def test_get_ec2_recommendations(self, compute_optimizer, mock_compute_optimizer_client):
        """Test getting EC2 recommendations"""
        # Mock EC2 recommendations response
        mock_compute_optimizer_client.get_ec2_instance_recommendations.return_value = {
            'instanceRecommendations': [
                {
                    'instanceArn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0',
                    'instanceName': 'test-instance',
                    'currentInstanceType': 't3.large',
                    'finding': 'Overprovisioned',
                    'recommendationOptions': [
                        {
                            'instanceType': 't3.medium'
                        }
                    ]
                }
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            # Mock core get_account_info
            with patch.object(compute_optimizer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
                recommendations = await compute_optimizer.get_ec2_recommendations()
                
                assert len(recommendations) == 1
                rec = recommendations[0]
                assert rec.service == 'compute-optimizer'
                assert rec.resource_id == 'i-1234567890abcdef0'
                assert rec.resource_type == 'EC2 Instance'
                assert rec.recommendation_type == 'Rightsizing - Overprovisioned'
                assert rec.confidence == 'HIGH'
                assert 't3.large → t3.medium' in rec.description
                assert rec.estimated_savings == 150.0  # Overprovisioned savings
    
    @pytest.mark.asyncio
    async def test_get_ebs_recommendations(self, compute_optimizer, mock_compute_optimizer_client):
        """Test getting EBS recommendations"""
        # Mock EBS recommendations response
        mock_compute_optimizer_client.get_ebs_volume_recommendations.return_value = {
            'volumeRecommendations': [
                {
                    'volumeArn': 'arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0',
                    'currentConfiguration': {
                        'volumeType': 'gp2',
                        'volumeSize': 100
                    },
                    'finding': 'Overprovisioned',
                    'volumeRecommendationOptions': [
                        {
                            'configuration': {
                                'volumeType': 'gp3',
                                'volumeSize': 50
                            }
                        }
                    ]
                }
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            # Mock core get_account_info
            with patch.object(compute_optimizer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
                recommendations = await compute_optimizer.get_ebs_recommendations()
                
                assert len(recommendations) == 1
                rec = recommendations[0]
                assert rec.service == 'compute-optimizer'
                assert rec.resource_id == 'vol-1234567890abcdef0'
                assert rec.resource_type == 'EBS Volume'
                assert rec.recommendation_type == 'Volume Optimization - Overprovisioned'
                assert rec.confidence == 'HIGH'
                assert 'gp2 100GB → gp3 50GB' in rec.description
                assert rec.estimated_savings == 5.0  # 50GB difference * $0.10
    
    @pytest.mark.asyncio
    async def test_get_lambda_recommendations(self, compute_optimizer, mock_compute_optimizer_client):
        """Test getting Lambda recommendations"""
        # Mock Lambda recommendations response
        mock_compute_optimizer_client.get_lambda_function_recommendations.return_value = {
            'lambdaFunctionRecommendations': [
                {
                    'functionArn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
                    'functionVersion': '$LATEST',
                    'currentMemorySize': 1024,
                    'finding': 'Overprovisioned',
                    'memorySizeRecommendationOptions': [
                        {
                            'memorySize': 512
                        }
                    ]
                }
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            # Mock core get_account_info
            with patch.object(compute_optimizer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
                recommendations = await compute_optimizer.get_lambda_recommendations()
                
                assert len(recommendations) == 1
                rec = recommendations[0]
                assert rec.service == 'compute-optimizer'
                assert rec.resource_id == 'test-function'
                assert rec.resource_type == 'Lambda Function'
                assert rec.recommendation_type == 'Memory Optimization - Overprovisioned'
                assert rec.confidence == 'HIGH'
                assert '1024MB → 512MB' in rec.description
                assert rec.estimated_savings == 0.512  # 512MB difference * $0.001
    
    @pytest.mark.asyncio
    async def test_get_auto_scaling_recommendations(self, compute_optimizer, mock_compute_optimizer_client):
        """Test getting Auto Scaling Group recommendations"""
        # Mock ASG recommendations response
        mock_compute_optimizer_client.get_auto_scaling_group_recommendations.return_value = {
            'autoScalingGroupRecommendations': [
                {
                    'autoScalingGroupArn': 'arn:aws:autoscaling:us-east-1:123456789012:autoScalingGroup:uuid:autoScalingGroupName/test-asg',
                    'autoScalingGroupName': 'test-asg',
                    'currentConfiguration': {
                        'instanceType': 't3.large'
                    },
                    'finding': 'Overprovisioned',
                    'recommendationOptions': [
                        {
                            'configuration': {
                                'instanceType': 't3.medium'
                            }
                        }
                    ]
                }
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            # Mock core get_account_info
            with patch.object(compute_optimizer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
                recommendations = await compute_optimizer.get_auto_scaling_recommendations()
                
                assert len(recommendations) == 1
                rec = recommendations[0]
                assert rec.service == 'compute-optimizer'
                assert rec.resource_id == 'test-asg'
                assert rec.resource_type == 'Auto Scaling Group'
                assert rec.recommendation_type == 'ASG Optimization - Overprovisioned'
                assert rec.confidence == 'HIGH'
                assert 't3.large → t3.medium' in rec.description
                assert rec.estimated_savings == 200.0  # ASG overprovisioned savings
    
    @pytest.mark.asyncio
    async def test_get_ecs_recommendations(self, compute_optimizer, mock_compute_optimizer_client):
        """Test getting ECS recommendations"""
        # Mock ECS recommendations response
        mock_compute_optimizer_client.get_ecs_service_recommendations.return_value = {
            'ecsServiceRecommendations': [
                {
                    'serviceArn': 'arn:aws:ecs:us-east-1:123456789012:service/test-cluster/test-service',
                    'currentServiceConfiguration': {
                        'cpu': 1024,
                        'memory': 2048
                    },
                    'finding': 'Overprovisioned',
                    'serviceRecommendationOptions': [
                        {
                            'containerRecommendations': [
                                {
                                    'cpu': 512,
                                    'memory': 1024
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        with patch('aws_super_cli.aws.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_compute_optimizer_client
            
            # Mock core get_account_info
            with patch.object(compute_optimizer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
                recommendations = await compute_optimizer.get_ecs_recommendations()
                
                assert len(recommendations) == 1
                rec = recommendations[0]
                assert rec.service == 'compute-optimizer'
                assert rec.resource_id == 'test-service'
                assert rec.resource_type == 'ECS Service'
                assert rec.recommendation_type == 'ECS Optimization - Overprovisioned'
                assert rec.confidence == 'HIGH'
                assert '1024CPU/2048MB → 512CPU/1024MB' in rec.description
                # CPU diff: 512 * 0.04 = 20.48, Memory diff: 1024 * 0.004 = 4.096
                assert rec.estimated_savings == 24.576
    
    @pytest.mark.asyncio
    async def test_get_all_recommendations_enrolled(self, compute_optimizer):
        """Test getting all recommendations when enrolled"""
        # Mock enrollment status as active
        with patch.object(compute_optimizer, 'check_enrollment_status', return_value={'enrolled': True}):
            # Mock individual recommendation methods
            with patch.object(compute_optimizer, 'get_ec2_recommendations', return_value=[Mock()]):
                with patch.object(compute_optimizer, 'get_ebs_recommendations', return_value=[Mock()]):
                    with patch.object(compute_optimizer, 'get_lambda_recommendations', return_value=[Mock()]):
                        with patch.object(compute_optimizer, 'get_auto_scaling_recommendations', return_value=[Mock()]):
                            with patch.object(compute_optimizer, 'get_ecs_recommendations', return_value=[Mock()]):
                                recommendations = await compute_optimizer.get_all_recommendations()
                                
                                assert len(recommendations) == 5  # One from each service
    
    @pytest.mark.asyncio
    async def test_get_all_recommendations_not_enrolled_access_denied(self, compute_optimizer):
        """Test getting recommendations when not enrolled due to access denied"""
        # Mock enrollment status as not enrolled with access denied
        with patch.object(compute_optimizer, 'check_enrollment_status', return_value={
            'enrolled': False,
            'error_code': 'ACCESS_DENIED',
            'message': 'ComputeOptimizerReadOnlyAccess IAM policy required'
        }):
            with pytest.raises(OptimizationError) as exc_info:
                await compute_optimizer.get_all_recommendations()
            
            assert exc_info.value.error_code == 'ACCESS_DENIED'
            assert 'ComputeOptimizerReadOnlyAccess' in exc_info.value.remediation
    
    @pytest.mark.asyncio
    async def test_get_all_recommendations_not_enrolled_activation_success(self, compute_optimizer):
        """Test getting recommendations when not enrolled but activation succeeds"""
        # Mock enrollment status as not enrolled
        with patch.object(compute_optimizer, 'check_enrollment_status', return_value={
            'enrolled': False,
            'status': 'Inactive',
            'status_reason': 'Not enrolled'
        }):
            # Mock successful activation
            with patch.object(compute_optimizer, 'activate_enrollment', return_value={'success': True}):
                # Mock individual recommendation methods
                with patch.object(compute_optimizer, 'get_ec2_recommendations', return_value=[]):
                    with patch.object(compute_optimizer, 'get_ebs_recommendations', return_value=[]):
                        with patch.object(compute_optimizer, 'get_lambda_recommendations', return_value=[]):
                            with patch.object(compute_optimizer, 'get_auto_scaling_recommendations', return_value=[]):
                                with patch.object(compute_optimizer, 'get_ecs_recommendations', return_value=[]):
                                    recommendations = await compute_optimizer.get_all_recommendations()
                                    
                                    assert len(recommendations) == 0  # No recommendations yet after activation
    
    @pytest.mark.asyncio
    async def test_get_all_recommendations_not_enrolled_activation_failed(self, compute_optimizer):
        """Test getting recommendations when not enrolled and activation fails"""
        # Mock enrollment status as not enrolled
        with patch.object(compute_optimizer, 'check_enrollment_status', return_value={
            'enrolled': False,
            'status': 'Inactive',
            'status_reason': 'Not enrolled'
        }):
            # Mock failed activation
            with patch.object(compute_optimizer, 'activate_enrollment', return_value={'success': False}):
                with pytest.raises(OptimizationError) as exc_info:
                    await compute_optimizer.get_all_recommendations()
                
                assert exc_info.value.error_code == 'NOT_ENROLLED'
    
    def test_calculate_savings_methods(self, compute_optimizer):
        """Test savings calculation methods"""
        # Test EC2 savings
        assert compute_optimizer._calculate_ec2_savings('t3.large', 't3.medium', 'Overprovisioned') == 150.0
        assert compute_optimizer._calculate_ec2_savings('t3.small', 't3.medium', 'Underprovisioned') == 0.0
        assert compute_optimizer._calculate_ec2_savings('t3.medium', 't3.medium', 'Optimized') == 0.0
        
        # Test EBS savings
        assert compute_optimizer._calculate_ebs_savings('gp2', 100, 'gp3', 50, 'Overprovisioned') == 5.0
        assert compute_optimizer._calculate_ebs_savings('gp2', 50, 'gp3', 100, 'Underprovisioned') == 0.0
        
        # Test Lambda savings
        assert compute_optimizer._calculate_lambda_savings(1024, 512, 'Overprovisioned') == 0.512
        assert compute_optimizer._calculate_lambda_savings(512, 1024, 'Underprovisioned') == 0.0
        
        # Test ASG savings
        assert compute_optimizer._calculate_asg_savings('t3.large', 't3.medium', 'Overprovisioned') == 200.0
        assert compute_optimizer._calculate_asg_savings('t3.small', 't3.medium', 'Underprovisioned') == 0.0
        
        # Test ECS savings
        assert compute_optimizer._calculate_ecs_savings(1024, 2048, 512, 1024, 'Overprovisioned') == 24.576
        assert compute_optimizer._calculate_ecs_savings(512, 1024, 1024, 2048, 'Underprovisioned') == 0.0
    
    def test_get_confidence_from_finding(self, compute_optimizer):
        """Test confidence mapping from findings"""
        assert compute_optimizer._get_confidence_from_finding('Overprovisioned') == 'HIGH'
        assert compute_optimizer._get_confidence_from_finding('Underprovisioned') == 'HIGH'
        assert compute_optimizer._get_confidence_from_finding('Optimized') == 'LOW'
        assert compute_optimizer._get_confidence_from_finding('Unknown') == 'MEDIUM'
    
    def test_extract_region_from_arn(self, compute_optimizer):
        """Test region extraction from ARN"""
        arn = 'arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0'
        assert compute_optimizer._extract_region_from_arn(arn) == 'us-east-1'
        
        # Test invalid ARN
        assert compute_optimizer._extract_region_from_arn('invalid-arn') == 'unknown'
        assert compute_optimizer._extract_region_from_arn('') == 'unknown'
    
    def test_create_compute_optimizer_summary_table(self, compute_optimizer):
        """Test creating summary table"""
        # Create mock recommendations
        recommendations = [
            OptimizationRecommendation(
                service='compute-optimizer',
                resource_id='i-123',
                resource_type='EC2 Instance',
                recommendation_type='Rightsizing',
                current_cost=100.0,
                estimated_savings=50.0,
                confidence='HIGH',
                description='Test EC2 recommendation',
                remediation_steps=[],
                region='us-east-1',
                account_id='123456789012',
                timestamp=datetime.now().isoformat(),
                source='compute_optimizer'
            ),
            OptimizationRecommendation(
                service='compute-optimizer',
                resource_id='vol-456',
                resource_type='EBS Volume',
                recommendation_type='Volume Optimization',
                current_cost=20.0,
                estimated_savings=10.0,
                confidence='MEDIUM',
                description='Test EBS recommendation',
                remediation_steps=[],
                region='us-east-1',
                account_id='123456789012',
                timestamp=datetime.now().isoformat(),
                source='compute_optimizer'
            )
        ]
        
        table = compute_optimizer.create_compute_optimizer_summary_table(recommendations)
        
        # Verify table structure
        assert table.title == "Compute Optimizer Cost Optimization Summary"
        assert len(table.columns) == 4  # Service Type, Resources, Est. Savings, Avg Confidence
        
        # Should have 3 rows: EC2, EBS, and TOTAL
        assert len(table.rows) == 3