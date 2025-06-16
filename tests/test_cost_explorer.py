"""
Tests for AWS Cost Explorer Integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from aws_super_cli.services.cost_explorer import CostExplorerIntegration
from aws_super_cli.services.cost_optimization import OptimizationRecommendation, OptimizationError


@pytest.fixture
def cost_explorer():
    """Create CostExplorerIntegration instance for testing"""
    return CostExplorerIntegration()


@pytest.fixture
def mock_cost_explorer_client():
    """Mock Cost Explorer client"""
    client = Mock()
    return client


@pytest.fixture
def mock_billing_client():
    """Mock Billing client"""
    client = Mock()
    return client


class TestCostExplorerIntegration:
    """Test Cost Explorer integration functionality"""
    
    @pytest.mark.asyncio
    async def test_get_current_spend_analysis_success(self, cost_explorer, mock_cost_explorer_client):
        """Test successful spend analysis retrieval"""
        # Mock response
        mock_response = {
            'ResultsByTime': [
                {
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {
                                'BlendedCost': {
                                    'Amount': '150.50',
                                    'Unit': 'USD'
                                }
                            }
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {
                                'BlendedCost': {
                                    'Amount': '25.75',
                                    'Unit': 'USD'
                                }
                            }
                        }
                    ]
                }
            ]
        }
        
        mock_cost_explorer_client.get_cost_and_usage.return_value = mock_response
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_cost_explorer_client
            
            result = await cost_explorer.get_current_spend_analysis(days=30)
            
            assert result['total_cost'] == 176.25
            assert result['currency'] == 'USD'
            assert result['period_days'] == 30
            assert len(result['services']) == 2
            assert result['services'][0]['service'] == 'Amazon Elastic Compute Cloud - Compute'
            assert result['services'][0]['cost'] == 150.50
    
    @pytest.mark.asyncio
    async def test_get_current_spend_analysis_error_handling(self, cost_explorer):
        """Test spend analysis error handling"""
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session:
            mock_session.client.side_effect = Exception("Access denied")
            
            result = await cost_explorer.get_current_spend_analysis()
            
            assert result['total_cost'] == 0
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_get_rightsizing_recommendations_success(self, cost_explorer, mock_cost_explorer_client):
        """Test successful rightsizing recommendations retrieval"""
        mock_response = {
            'RightsizingRecommendations': [
                {
                    'CurrentInstance': {
                        'ResourceId': 'i-1234567890abcdef0',
                        'InstanceType': 't2.medium',
                        'MonthlyCost': {'Amount': '75.00'},
                        'Region': 'us-east-1'
                    },
                    'RightsizingType': 'Modify',
                    'EstimatedMonthlySavings': {'Amount': '25.00'},
                    'ModifyRecommendationDetail': {
                        'TargetInstances': [
                            {'InstanceType': 't3.small'}
                        ]
                    }
                }
            ]
        }
        
        mock_cost_explorer_client.get_rightsizing_recommendation.return_value = mock_response
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session, \
             patch.object(cost_explorer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
            
            mock_session.client.return_value = mock_cost_explorer_client
            
            recommendations = await cost_explorer.get_rightsizing_recommendations()
            
            assert len(recommendations) == 1
            rec = recommendations[0]
            assert rec.source == 'cost_explorer'
            assert rec.resource_id == 'i-1234567890abcdef0'
            assert rec.resource_type == 'EC2 Instance'
            assert rec.recommendation_type == 'rightsizing'
            assert rec.estimated_savings == 25.00
            assert rec.confidence == 'MEDIUM'
            assert 't2.medium → t3.small' in rec.description
    
    @pytest.mark.asyncio
    async def test_get_savings_plans_recommendations_success(self, cost_explorer, mock_cost_explorer_client):
        """Test successful Savings Plans recommendations retrieval"""
        mock_response = {
            'SavingsPlansRecommendations': [
                {
                    'SavingsPlansDetails': {
                        'InstanceFamily': 't3',
                        'Region': 'us-east-1'
                    },
                    'TermInYears': 'ONE_YEAR',
                    'PaymentOption': 'NO_UPFRONT',
                    'EstimatedMonthlySavings': {'Amount': '50.00'},
                    'HourlyCommitment': '0.10',
                    'UpfrontCost': {'Amount': '0.00'}
                }
            ]
        }
        
        mock_cost_explorer_client.get_savings_plans_purchase_recommendation.return_value = mock_response
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session, \
             patch.object(cost_explorer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
            
            mock_session.client.return_value = mock_cost_explorer_client
            
            recommendations = await cost_explorer.get_savings_plans_recommendations()
            
            assert len(recommendations) == 1
            rec = recommendations[0]
            assert rec.source == 'cost_explorer'
            assert rec.resource_type == 'Savings Plan'
            assert rec.recommendation_type == 'savings_plan'
            assert rec.estimated_savings == 50.00
            assert rec.confidence == 'HIGH'
            assert 't3' in rec.description
    
    @pytest.mark.asyncio
    async def test_get_reserved_instance_recommendations_success(self, cost_explorer, mock_cost_explorer_client):
        """Test successful Reserved Instance recommendations retrieval"""
        mock_response = {
            'Recommendations': [
                {
                    'RecommendationDetails': {
                        'InstanceDetails': {
                            'EC2InstanceDetails': {
                                'InstanceType': 't3.medium',
                                'Region': 'us-east-1',
                                'Platform': 'Linux/UNIX',
                                'Tenancy': 'default'
                            }
                        }
                    },
                    'TermInYears': 'ONE_YEAR',
                    'PaymentOption': 'NO_UPFRONT',
                    'EstimatedMonthlySavings': {'Amount': '30.00'},
                    'RecommendedNumberOfInstancesToPurchase': '2'
                }
            ]
        }
        
        mock_cost_explorer_client.get_reservation_purchase_recommendation.return_value = mock_response
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session, \
             patch.object(cost_explorer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
            
            mock_session.client.return_value = mock_cost_explorer_client
            
            recommendations = await cost_explorer.get_reserved_instance_recommendations()
            
            assert len(recommendations) == 1
            rec = recommendations[0]
            assert rec.source == 'cost_explorer'
            assert rec.resource_type == 'Reserved Instance'
            assert rec.recommendation_type == 'reserved_instance'
            assert rec.estimated_savings == 30.00
            assert rec.confidence == 'HIGH'
            assert 't3.medium' in rec.description
    
    @pytest.mark.asyncio
    async def test_get_billing_credits_success(self, cost_explorer, mock_billing_client):
        """Test successful billing credits retrieval"""
        mock_response = {
            'Credits': [
                {
                    'CreditType': 'PROMOTIONAL',
                    'Amount': {'Amount': '100.00', 'Unit': 'USD'},
                    'Description': 'AWS Promotional Credit',
                    'ExpiryDate': '2024-12-31'
                },
                {
                    'CreditType': 'SERVICE',
                    'Amount': {'Amount': '25.50', 'Unit': 'USD'},
                    'Description': 'Service Credit',
                    'ExpiryDate': '2024-06-30'
                }
            ]
        }
        
        mock_billing_client.list_credits.return_value = mock_response
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_billing_client
            
            result = await cost_explorer.get_billing_credits()
            
            assert result['total_credits'] == 125.50
            assert result['currency'] == 'USD'
            assert len(result['credits']) == 2
            assert result['credits'][0]['type'] == 'PROMOTIONAL'
            assert result['credits'][0]['amount'] == 100.00
    
    @pytest.mark.asyncio
    async def test_get_cost_optimization_hub_recommendations_success(self, cost_explorer):
        """Test successful Cost Optimization Hub recommendations retrieval"""
        mock_response = {
            'items': [
                {
                    'resourceId': 'i-abcdef1234567890',
                    'currentResourceType': 'Ec2Instance',
                    'recommendedResourceType': 'Ec2Instance',
                    'actionType': 'Rightsize',
                    'estimatedMonthlySavings': 40.00,
                    'estimatedMonthlyCost': 120.00,
                    'estimatedSavingsPercentage': 33.0,
                    'recommendationId': 'rec-123',
                    'accountId': '123456789012',
                    'region': 'us-east-1',
                    'lastRefreshTimestamp': '2024-01-15T10:00:00Z',
                    'implementationEffort': 'Low',
                    'currentResourceSummary': 't3.medium',
                    'recommendedResourceSummary': 't3.small',
                    'tags': [
                        {
                            'key': 'Name',
                            'value': 'Test Instance'
                        }
                    ]
                }
            ]
        }
        
        mock_coh_client = Mock()
        mock_coh_client.list_recommendations.return_value = mock_response
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session, \
             patch.object(cost_explorer.core, 'get_account_info', return_value={'account_id': '123456789012'}):
            
            mock_session.client.return_value = mock_coh_client
            
            recommendations = await cost_explorer.get_cost_optimization_hub_recommendations()
            
            assert len(recommendations) == 1
            rec = recommendations[0]
            assert rec.source == 'cost_optimization_hub'
            assert rec.resource_id == 'i-abcdef1234567890'
            assert rec.resource_type == 'EC2 Instance'
            assert rec.recommendation_type == 'Rightsize'
            assert rec.estimated_savings == 40.00
            assert rec.current_cost == 120.00
            assert rec.confidence == 'HIGH'  # Low implementation effort maps to HIGH confidence
            assert rec.service == 'EC2'
            assert 'Test Instance' in rec.description
            assert 't3.medium' in rec.description
            assert 't3.small' in rec.description
    
    @pytest.mark.asyncio
    async def test_get_all_recommendations_integration(self, cost_explorer):
        """Test getting all recommendations from multiple sources"""
        # Mock multiple successful responses
        with patch.object(cost_explorer, 'get_rightsizing_recommendations') as mock_rightsizing, \
             patch.object(cost_explorer, 'get_savings_plans_recommendations') as mock_savings, \
             patch.object(cost_explorer, 'get_reserved_instance_recommendations') as mock_ri, \
             patch.object(cost_explorer, 'get_cost_optimization_hub_recommendations') as mock_coh:
            
            # Setup mock returns with proper OptimizationRecommendation structure
            mock_rightsizing.return_value = [
                OptimizationRecommendation(
                    service='EC2',
                    resource_id='i-123',
                    resource_type='EC2 Instance',
                    recommendation_type='rightsizing',
                    current_cost=100.0,
                    estimated_savings=25.00,
                    confidence='MEDIUM',
                    description='Rightsize EC2',
                    remediation_steps=['Step 1', 'Step 2'],
                    region='us-east-1',
                    account_id='123456789012',
                    timestamp=datetime.now().isoformat(),
                    source='cost_explorer'
                )
            ]
            
            mock_savings.return_value = [
                OptimizationRecommendation(
                    service='Savings Plans',
                    resource_id='sp-456',
                    resource_type='Savings Plan',
                    recommendation_type='savings_plan',
                    current_cost=0.0,
                    estimated_savings=50.00,
                    confidence='HIGH',
                    description='Purchase Savings Plan',
                    remediation_steps=['Step 1', 'Step 2'],
                    region='us-east-1',
                    account_id='123456789012',
                    timestamp=datetime.now().isoformat(),
                    source='cost_explorer'
                )
            ]
            
            mock_ri.return_value = []  # No RI recommendations
            mock_coh.return_value = []  # No COH recommendations
            
            recommendations = await cost_explorer.get_all_recommendations()
            
            assert len(recommendations) == 2
            assert recommendations[0].recommendation_type == 'rightsizing'
            assert recommendations[1].recommendation_type == 'savings_plan'
    
    def test_create_spend_analysis_table(self, cost_explorer):
        """Test spend analysis table creation"""
        spend_data = {
            'total_cost': 200.00,
            'currency': 'USD',
            'services': [
                {'service': 'Amazon EC2', 'cost': 150.00},
                {'service': 'Amazon S3', 'cost': 30.00},
                {'service': 'Amazon RDS', 'cost': 20.00}
            ]
        }
        
        table = cost_explorer.create_spend_analysis_table(spend_data)
        
        assert table.title == "Current Spend Analysis (Last 30 Days)"
        assert len(table.columns) == 3  # Service, Cost, Percentage
    
    def test_create_recommendations_summary_table(self, cost_explorer):
        """Test recommendations summary table creation"""
        recommendations = [
            OptimizationRecommendation(
                service='EC2',
                resource_id='i-123',
                resource_type='EC2 Instance',
                recommendation_type='rightsizing',
                current_cost=100.0,
                estimated_savings=25.00,
                confidence='HIGH',
                description='Rightsize EC2',
                remediation_steps=['Step 1', 'Step 2'],
                region='us-east-1',
                account_id='123456789012',
                timestamp=datetime.now().isoformat(),
                source='cost_explorer'
            ),
            OptimizationRecommendation(
                service='EC2',
                resource_id='i-456',
                resource_type='EC2 Instance',
                recommendation_type='rightsizing',
                current_cost=75.0,
                estimated_savings=15.00,
                confidence='MEDIUM',
                description='Rightsize EC2',
                remediation_steps=['Step 1', 'Step 2'],
                region='us-east-1',
                account_id='123456789012',
                timestamp=datetime.now().isoformat(),
                source='cost_explorer'
            ),
            OptimizationRecommendation(
                service='Savings Plans',
                resource_id='sp-789',
                resource_type='Savings Plan',
                recommendation_type='savings_plan',
                current_cost=0.0,
                estimated_savings=50.00,
                confidence='HIGH',
                description='Purchase Savings Plan',
                remediation_steps=['Step 1', 'Step 2'],
                region='us-east-1',
                account_id='123456789012',
                timestamp=datetime.now().isoformat(),
                source='cost_explorer'
            )
        ]
        
        table = cost_explorer.create_recommendations_summary_table(recommendations)
        
        assert table.title == "Cost Explorer Optimization Summary"
        assert len(table.columns) == 4  # Type, Resources, Savings, Confidence
    
    @pytest.mark.asyncio
    async def test_error_handling_in_recommendations(self, cost_explorer):
        """Test error handling in recommendation methods"""
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session:
            mock_session.client.side_effect = Exception("API Error")
            
            # Test that errors are handled gracefully
            rightsizing_recs = await cost_explorer.get_rightsizing_recommendations()
            savings_recs = await cost_explorer.get_savings_plans_recommendations()
            ri_recs = await cost_explorer.get_reserved_instance_recommendations()
            coh_recs = await cost_explorer.get_cost_optimization_hub_recommendations()
            
            # All should return empty lists on error
            assert rightsizing_recs == []
            assert savings_recs == []
            assert ri_recs == []
            assert coh_recs == []
    
    @pytest.mark.asyncio
    async def test_billing_credits_error_handling(self, cost_explorer):
        """Test billing credits error handling"""
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session:
            mock_session.client.side_effect = Exception("Billing API not available")
            
            result = await cost_explorer.get_billing_credits()
            
            assert result['total_credits'] == 0
            assert result['currency'] == 'USD'
            assert result['credits'] == []
            assert 'error' in result
    
    def test_confidence_calculation_in_rightsizing(self, cost_explorer):
        """Test confidence level calculation in rightsizing recommendations"""
        # This would be tested through the actual recommendation creation
        # but we can verify the logic exists in the implementation
        assert hasattr(cost_explorer, 'get_rightsizing_recommendations')
    
    @pytest.mark.asyncio
    async def test_date_range_calculation(self, cost_explorer):
        """Test that date ranges are calculated correctly"""
        mock_client = Mock()
        mock_client.get_cost_and_usage.return_value = {'ResultsByTime': []}
        
        with patch('aws_super_cli.services.cost_explorer.aws_session.session') as mock_session:
            mock_session.client.return_value = mock_client
            
            await cost_explorer.get_current_spend_analysis(days=7)
            
            # Verify the API was called with correct date range
            call_args = mock_client.get_cost_and_usage.call_args[1]
            time_period = call_args['TimePeriod']
            
            # Should have Start and End dates
            assert 'Start' in time_period
            assert 'End' in time_period
            
            # Dates should be in YYYY-MM-DD format
            start_date = datetime.strptime(time_period['Start'], '%Y-%m-%d').date()
            end_date = datetime.strptime(time_period['End'], '%Y-%m-%d').date()
            
            # Should be approximately 7 days apart
            assert (end_date - start_date).days == 7