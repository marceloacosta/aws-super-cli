"""Tests for AWS Service Quotas Integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from aws_super_cli.services.service_quotas import ServiceQuotasIntegration
from aws_super_cli.services.cost_optimization import OptimizationRecommendation


@pytest.fixture
def mock_aws_session():
    """Mock AWS session for testing."""
    session = Mock()
    session.session = Mock()
    session.account_id = "123456789012"
    return session


@pytest.fixture
def service_quotas_integration(mock_aws_session):
    """Create ServiceQuotasIntegration instance for testing."""
    return ServiceQuotasIntegration(mock_aws_session)


@pytest.fixture
def mock_quota_data():
    """Mock quota utilization data."""
    return [
        {
            'service_code': 'ec2',
            'service_name': 'Amazon Elastic Compute Cloud (Amazon EC2)',
            'quota_name': 'Running On-Demand EC2 Instances',
            'quota_arn': 'arn:aws:servicequotas:us-east-1:123456789012:ec2/L-1216C47A',
            'quota_value': 20.0,
            'current_usage': 18.0,
            'utilization_percentage': 90.0,
            'available_capacity': 2.0
        },
        {
            'service_code': 'rds',
            'service_name': 'Amazon Relational Database Service (Amazon RDS)',
            'quota_name': 'DB instances',
            'quota_arn': 'arn:aws:servicequotas:us-east-1:123456789012:rds/L-7B6409FD',
            'quota_value': 40.0,
            'current_usage': 25.0,
            'utilization_percentage': 62.5,
            'available_capacity': 15.0
        },
        {
            'service_code': 's3',
            'service_name': 'Amazon Simple Storage Service (Amazon S3)',
            'quota_name': 'Buckets',
            'quota_arn': 'arn:aws:servicequotas:us-east-1:123456789012:s3/L-DC2B2D3D',
            'quota_value': 100.0,
            'current_usage': 95.0,
            'utilization_percentage': 95.0,
            'available_capacity': 5.0
        }
    ]


class TestServiceQuotasIntegration:
    """Test Service Quotas integration functionality."""
    
    @pytest.mark.asyncio
    async def test_get_quota_recommendations_success(self, service_quotas_integration):
        mock_quota_data = [{
            "service_code": "ec2",
            "service_name": "Amazon EC2",
            "quota_name": "Running Instances",
            "quota_value": 20.0,
            "current_usage": 18.0,
            "utilization_percentage": 90.0,
            "available_capacity": 2.0
        }]
        
        with patch.object(service_quotas_integration, "_get_quota_utilization", return_value=mock_quota_data):
            recommendations = await service_quotas_integration.get_quota_recommendations()
            
            assert len(recommendations) == 1
            assert recommendations[0].service == "service-quotas"
            assert recommendations[0].confidence == "High"
    
    @pytest.mark.asyncio
    async def test_get_quota_recommendations_error_handling(self, service_quotas_integration):
        with patch.object(service_quotas_integration, "_get_quota_utilization", side_effect=Exception("API Error")):
            recommendations = await service_quotas_integration.get_quota_recommendations()
            assert recommendations == []
    
    @pytest.mark.asyncio
    async def test_get_quota_utilization_success(self, service_quotas_integration):
        """Test successful quota utilization data retrieval."""
        mock_services_response = {
            'Services': [
                {'ServiceCode': 'ec2', 'ServiceName': 'Amazon EC2'},
                {'ServiceCode': 'rds', 'ServiceName': 'Amazon RDS'}
            ]
        }
        
        mock_quotas_response = {
            'Quotas': [
                {
                    'QuotaName': 'Running On-Demand EC2 Instances',
                    'Value': 20.0,
                    'QuotaArn': 'arn:aws:servicequotas:us-east-1:123456789012:ec2/L-1216C47A'
                }
            ]
        }
        
        mock_quotas_client = Mock()
        mock_quotas_client.list_services.return_value = mock_services_response
        mock_quotas_client.list_service_quotas.return_value = mock_quotas_response
        
        mock_cloudwatch_client = Mock()
        
        service_quotas_integration.aws_session.session.client.side_effect = lambda service: {
            'service-quotas': mock_quotas_client,
            'cloudwatch': mock_cloudwatch_client
        }[service]
        
        with patch.object(service_quotas_integration, '_analyze_quota_utilization') as mock_analyze:
            mock_analyze.return_value = {
                'service_code': 'ec2',
                'service_name': 'Amazon EC2',
                'quota_name': 'Running On-Demand EC2 Instances',
                'quota_value': 20.0,
                'current_usage': 15.0,
                'utilization_percentage': 75.0,
                'available_capacity': 5.0
            }
            
            quota_data = await service_quotas_integration._get_quota_utilization()
            
            assert len(quota_data) == 1
            assert quota_data[0]['utilization_percentage'] == 75.0
    
    @pytest.mark.asyncio
    async def test_analyze_quota_utilization_with_cloudwatch(self, service_quotas_integration):
        """Test quota utilization analysis with CloudWatch data."""
        quota = {
            'QuotaName': 'Running On-Demand EC2 Instances',
            'Value': 20.0,
            'QuotaArn': 'arn:aws:servicequotas:us-east-1:123456789012:ec2/L-1216C47A'
        }
        
        mock_cloudwatch_client = Mock()
        
        with patch.object(service_quotas_integration, '_get_quota_usage_from_cloudwatch', return_value=15.0):
            result = await service_quotas_integration._analyze_quota_utilization(
                quota, 'ec2', 'Amazon EC2', mock_cloudwatch_client
            )
            
            assert result is not None
            assert result['quota_value'] == 20.0
            assert result['current_usage'] == 15.0
            assert result['utilization_percentage'] == 75.0
            assert result['available_capacity'] == 5.0
    
    @pytest.mark.asyncio
    async def test_analyze_quota_utilization_with_estimation(self, service_quotas_integration):
        """Test quota utilization analysis with usage estimation."""
        quota = {
            'QuotaName': 'Running On-Demand EC2 Instances',
            'Value': 20.0,
            'QuotaArn': 'arn:aws:servicequotas:us-east-1:123456789012:ec2/L-1216C47A'
        }
        
        mock_cloudwatch_client = Mock()
        
        with patch.object(service_quotas_integration, '_get_quota_usage_from_cloudwatch', return_value=None):
            with patch.object(service_quotas_integration, '_estimate_quota_usage', return_value=12.0):
                result = await service_quotas_integration._analyze_quota_utilization(
                    quota, 'ec2', 'Amazon EC2', mock_cloudwatch_client
                )
                
                assert result is not None
                assert result['current_usage'] == 12.0
                assert result['utilization_percentage'] == 60.0
    
    @pytest.mark.asyncio
    async def test_estimate_quota_usage_ec2(self, service_quotas_integration):
        """Test EC2 quota usage estimation."""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'i-1'}, {'InstanceId': 'i-2'}]},
                {'Instances': [{'InstanceId': 'i-3'}]}
            ]
        }
        
        service_quotas_integration.aws_session.session.client.return_value = mock_ec2_client
        
        usage = await service_quotas_integration._estimate_quota_usage('ec2', 'Running On-Demand EC2 Instances')
        
        assert usage == 3
        mock_ec2_client.describe_instances.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_estimate_quota_usage_rds(self, service_quotas_integration):
        """Test RDS quota usage estimation."""
        mock_rds_client = Mock()
        mock_rds_client.describe_db_instances.return_value = {
            'DBInstances': [
                {'DBInstanceIdentifier': 'db-1'},
                {'DBInstanceIdentifier': 'db-2'}
            ]
        }
        
        service_quotas_integration.aws_session.session.client.return_value = mock_rds_client
        
        usage = await service_quotas_integration._estimate_quota_usage('rds', 'DB instances')
        
        assert usage == 2
        mock_rds_client.describe_db_instances.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_estimate_quota_usage_s3(self, service_quotas_integration):
        """Test S3 quota usage estimation."""
        mock_s3_client = Mock()
        mock_s3_client.list_buckets.return_value = {
            'Buckets': [
                {'Name': 'bucket-1'},
                {'Name': 'bucket-2'},
                {'Name': 'bucket-3'}
            ]
        }
        
        service_quotas_integration.aws_session.session.client.return_value = mock_s3_client
        
        usage = await service_quotas_integration._estimate_quota_usage('s3', 'Buckets')
        
        assert usage == 3
        mock_s3_client.list_buckets.assert_called_once()
    
    def test_create_quota_recommendation_critical(self, service_quotas_integration):
        """Test creating critical quota recommendation."""
        quota = {
            "utilization_percentage": 95.0,
            "service_code": "s3",
            "service_name": "Amazon S3",
            "quota_name": "Buckets",
            "current_usage": 95.0,
            "quota_value": 100.0,
            "available_capacity": 5.0
        }
        
        recommendation = service_quotas_integration._create_quota_recommendation(quota)
        
        assert recommendation is not None
        assert recommendation.confidence == "Critical"
        assert "CRITICAL" in recommendation.description
    
    def test_create_quota_recommendation_high(self, service_quotas_integration):
        """Test creating high priority quota recommendation."""
        quota = {
            'utilization_percentage': 92.0,
            'service_name': 'Amazon EC2',
            'quota_name': 'Running Instances',
            'current_usage': 18.0,
            'quota_value': 20.0,
            'available_capacity': 2.0,
            'quota_arn': 'arn:aws:servicequotas:us-east-1:123456789012:ec2/L-1216C47A'
        }
        
        recommendation = service_quotas_integration._create_quota_recommendation(quota)
        
        assert recommendation is not None
        assert recommendation.confidence == "High"
        assert "HIGH" in recommendation.description
        assert "92.0%" in recommendation.description
    
    def test_create_quota_recommendation_medium(self, service_quotas_integration):
        """Test creating medium priority quota recommendation."""
        quota = {
            'utilization_percentage': 85.0,
            'service_name': 'Amazon RDS',
            'quota_name': 'DB instances',
            'current_usage': 34.0,
            'quota_value': 40.0,
            'available_capacity': 6.0,
            'quota_arn': 'arn:aws:servicequotas:us-east-1:123456789012:rds/L-7B6409FD'
        }
        
        recommendation = service_quotas_integration._create_quota_recommendation(quota)
        
        assert recommendation is not None
        assert recommendation.confidence == "Medium"
        assert "MEDIUM" in recommendation.description
        assert "85.0%" in recommendation.description
    
    def test_create_quota_utilization_table(self, service_quotas_integration, mock_quota_data):
        """Test creating quota utilization table."""
        table = service_quotas_integration.create_quota_utilization_table(mock_quota_data)
        
        assert table.title == "Service Quotas Utilization Analysis"
        assert len(table.columns) == 7
        assert table.columns[0].header == "Service"
        assert table.columns[1].header == "Quota Name"
        assert table.columns[2].header == "Usage"
        assert table.columns[3].header == "Limit"
        assert table.columns[4].header == "Utilization"
        assert table.columns[5].header == "Available"
        assert table.columns[6].header == "Status"
    
    def test_create_quota_recommendations_table(self, service_quotas_integration):
        """Test creating quota recommendations table."""
        recommendations = [
            OptimizationRecommendation(
                service="service-quotas",
                resource_id="ec2/Running On-Demand EC2 Instances",
                resource_type="quota",
                recommendation_type="quota_increase",
                current_cost=0.0,
                estimated_savings=0.0,
                confidence="High",
                description="HIGH: Running On-Demand EC2 Instances is at 90.0% capacity",
                remediation_steps=["Request quota increase for Running On-Demand EC2 Instances"],
                region="global",
                account_id="123456789012",
                timestamp=datetime.utcnow().isoformat(),
                source="service-quotas"
            )
        ]
        
        table = service_quotas_integration.create_quota_recommendations_table(recommendations)
        
        assert table.title == "Service Quotas Recommendations"
        assert len(table.columns) == 5
        assert table.columns[0].header == "Service"
        assert table.columns[1].header == "Quota"
        assert table.columns[2].header == "Urgency"
        assert table.columns[3].header == "Description"
        assert table.columns[4].header == "Action Required"
    
    @pytest.mark.asyncio
    async def test_get_quota_usage_from_cloudwatch_success(self, service_quotas_integration):
        """Test successful CloudWatch quota usage retrieval."""
        mock_cloudwatch_client = Mock()
        mock_cloudwatch_client.get_metric_statistics.return_value = {
            'Datapoints': [
                {'Maximum': 10.0},
                {'Maximum': 15.0},
                {'Maximum': 12.0}
            ]
        }
        
        usage = await service_quotas_integration._get_quota_usage_from_cloudwatch(
            'ec2', 'Running On-Demand EC2 Instances', mock_cloudwatch_client
        )
        
        assert usage == 15.0  # Maximum value
        mock_cloudwatch_client.get_metric_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_quota_usage_from_cloudwatch_no_data(self, service_quotas_integration):
        """Test CloudWatch quota usage with no data."""
        mock_cloudwatch_client = Mock()
        mock_cloudwatch_client.get_metric_statistics.return_value = {'Datapoints': []}
        
        usage = await service_quotas_integration._get_quota_usage_from_cloudwatch(
            'ec2', 'Running On-Demand EC2 Instances', mock_cloudwatch_client
        )
        
        assert usage is None
    
    @pytest.mark.asyncio
    async def test_get_quota_usage_from_cloudwatch_unmapped_service(self, service_quotas_integration):
        """Test CloudWatch quota usage for unmapped service."""
        mock_cloudwatch_client = Mock()
        
        usage = await service_quotas_integration._get_quota_usage_from_cloudwatch(
            'unknown-service', 'Some Quota', mock_cloudwatch_client
        )
        
        assert usage is None
        mock_cloudwatch_client.get_metric_statistics.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_estimate_quota_usage_unknown_service(self, service_quotas_integration):
        """Test quota usage estimation for unknown service."""
        usage = await service_quotas_integration._estimate_quota_usage('unknown-service', 'Some Quota')
        
        assert usage is None
    
    @pytest.mark.asyncio
    async def test_estimate_quota_usage_error_handling(self, service_quotas_integration):
        """Test error handling in quota usage estimation."""
        mock_ec2_client = Mock()
        mock_ec2_client.describe_instances.side_effect = Exception("API Error")
        
        service_quotas_integration.aws_session.session.client.return_value = mock_ec2_client
        
        usage = await service_quotas_integration._estimate_quota_usage('ec2', 'Running On-Demand EC2 Instances')
        
        assert usage is None
    
    def test_create_quota_recommendation_error_handling(self, service_quotas_integration):
        """Test error handling in quota recommendation creation."""
        # Invalid quota data
        quota = {}
        
        recommendation = service_quotas_integration._create_quota_recommendation(quota)
        
        assert recommendation is None 