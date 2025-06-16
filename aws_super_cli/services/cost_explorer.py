"""
AWS Cost Explorer Integration for Cost Analysis and Optimization
Provides comprehensive cost analysis, rightsizing recommendations, Savings Plans
suggestions, and billing credits tracking.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table

from ..aws import aws_session
from .cost_optimization import (
    OptimizationRecommendation, 
    CostOptimizationCore, 
    OptimizationError,
    handle_optimization_error
)


class CostExplorerIntegration:
    """AWS Cost Explorer integration for cost analysis and optimization recommendations"""
    
    def __init__(self, core: CostOptimizationCore = None):
        self.core = core or CostOptimizationCore()
        self.console = Console()
        
    async def get_current_spend_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Get current spend analysis using Cost Explorer GetCostAndUsage API"""
        try:
            session = aws_session.session
            ce_client = session.client('ce')
            
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get cost and usage data
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )
            
            # Process results
            total_cost = 0
            services_breakdown = []
            
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service_name = group['Keys'][0]
                    cost_amount = float(group['Metrics']['BlendedCost']['Amount'])
                    
                    if cost_amount > 0:
                        services_breakdown.append({
                            'service': service_name,
                            'cost': cost_amount,
                            'currency': group['Metrics']['BlendedCost']['Unit']
                        })
                        total_cost += cost_amount
            
            # Sort by cost descending
            services_breakdown.sort(key=lambda x: x['cost'], reverse=True)
            
            return {
                'total_cost': total_cost,
                'currency': 'USD',
                'period_days': days,
                'services': services_breakdown[:10],  # Top 10 services
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            handle_optimization_error(e, self.console)
            return {
                'total_cost': 0,
                'currency': 'USD',
                'period_days': days,
                'services': [],
                'error': str(e)
            }
    
    async def get_rightsizing_recommendations(self) -> List[OptimizationRecommendation]:
        """Get rightsizing recommendations from Cost Explorer"""
        recommendations = []
        
        try:
            session = aws_session.session
            ce_client = session.client('ce')
            
            response = ce_client.get_rightsizing_recommendation(
                Service='AmazonEC2',
                Configuration={
                    'BenefitsConsidered': True,
                    'RecommendationTarget': 'SAME_INSTANCE_FAMILY'
                }
            )
            
            # Get account info for recommendations
            account_info = await self.core.get_account_info()
            
            for rec in response.get('RightsizingRecommendations', []):
                resource_id = rec.get('CurrentInstance', {}).get('ResourceId', 'unknown')
                current_type = rec.get('CurrentInstance', {}).get('InstanceType', 'unknown')
                
                # Get recommended action
                action = rec.get('RightsizingType', 'unknown')
                
                # Calculate savings and current cost
                savings_amount = 0
                current_cost = 0
                if 'EstimatedMonthlySavings' in rec:
                    savings_amount = float(rec['EstimatedMonthlySavings'].get('Amount', 0))
                if 'CurrentInstance' in rec and 'MonthlyCost' in rec['CurrentInstance']:
                    current_cost = float(rec['CurrentInstance']['MonthlyCost'].get('Amount', 0))
                
                # Get recommended instance type
                recommended_type = current_type
                if rec.get('ModifyRecommendationDetail'):
                    target_instances = rec['ModifyRecommendationDetail'].get('TargetInstances', [])
                    if target_instances:
                        recommended_type = target_instances[0].get('InstanceType', current_type)
                
                # Determine confidence based on utilization
                confidence = 'MEDIUM'
                if current_cost > 100:
                    confidence = 'HIGH'
                elif current_cost < 50:
                    confidence = 'LOW'
                
                recommendation = OptimizationRecommendation(
                    service='EC2',
                    resource_id=resource_id,
                    resource_type='EC2 Instance',
                    recommendation_type='rightsizing',
                    current_cost=current_cost,
                    estimated_savings=savings_amount,
                    confidence=confidence,
                    description=f"EC2 instance {action}: {current_type} → {recommended_type}",
                    remediation_steps=[
                        f"Stop the EC2 instance {resource_id}",
                        f"Change instance type from {current_type} to {recommended_type}",
                        "Start the instance and verify functionality",
                        "Monitor performance for 24-48 hours"
                    ],
                    region=rec.get('CurrentInstance', {}).get('Region', 'unknown'),
                    account_id=account_info.get('account_id', 'unknown'),
                    timestamp=datetime.now().isoformat(),
                    source='cost_explorer'
                )
                
                recommendations.append(recommendation)
                
        except Exception as e:
            handle_optimization_error(e, self.console)
            
        return recommendations
    
    async def get_savings_plans_recommendations(self) -> List[OptimizationRecommendation]:
        """Get Savings Plans recommendations from Cost Explorer"""
        recommendations = []
        
        try:
            session = aws_session.session
            ce_client = session.client('ce')
            
            response = ce_client.get_savings_plans_purchase_recommendation(
                SavingsPlansType='COMPUTE_SP',
                TermInYears='ONE_YEAR',
                PaymentOption='NO_UPFRONT',
                LookbackPeriodInDays='SIXTY_DAYS'
            )
            
            # Get account info for recommendations
            account_info = await self.core.get_account_info()
            
            for rec in response.get('SavingsPlansRecommendations', []):
                details = rec.get('SavingsPlansDetails', {})
                
                # Calculate savings and costs
                savings_amount = 0
                upfront_cost = 0
                if 'EstimatedMonthlySavings' in rec:
                    savings_amount = float(rec['EstimatedMonthlySavings'].get('Amount', 0))
                if 'UpfrontCost' in rec:
                    upfront_cost = float(rec['UpfrontCost'].get('Amount', 0))
                
                recommendation = OptimizationRecommendation(
                    service='Savings Plans',
                    resource_id=f"savings-plan-{details.get('InstanceFamily', 'compute')}",
                    resource_type='Savings Plan',
                    recommendation_type='savings_plan',
                    current_cost=upfront_cost,
                    estimated_savings=savings_amount,
                    confidence='HIGH',
                    description=f"Savings Plan: {details.get('InstanceFamily', 'Compute')} - {rec.get('TermInYears', '1')} year",
                    remediation_steps=[
                        "Review the Savings Plan recommendation details",
                        "Purchase the recommended Savings Plan through AWS Console",
                        "Monitor usage to ensure optimal utilization",
                        "Set up billing alerts for Savings Plan utilization"
                    ],
                    region=details.get('Region', 'us-east-1'),
                    account_id=account_info.get('account_id', 'unknown'),
                    timestamp=datetime.now().isoformat(),
                    source='cost_explorer'
                )
                
                recommendations.append(recommendation)
                
        except Exception as e:
            handle_optimization_error(e, self.console)
            
        return recommendations
    
    async def get_reserved_instance_recommendations(self) -> List[OptimizationRecommendation]:
        """Get Reserved Instance recommendations from Cost Explorer"""
        recommendations = []
        
        try:
            session = aws_session.session
            ce_client = session.client('ce')
            
            response = ce_client.get_reservation_purchase_recommendation(
                Service='Amazon Elastic Compute Cloud - Compute',
                TermInYears='ONE_YEAR',
                PaymentOption='NO_UPFRONT',
                LookbackPeriodInDays='SIXTY_DAYS'
            )
            
            # Get account info for recommendations
            account_info = await self.core.get_account_info()
            
            for rec in response.get('Recommendations', []):
                details = rec.get('RecommendationDetails', {})
                instance_details = details.get('InstanceDetails', {}).get('EC2InstanceDetails', {})
                
                # Calculate savings
                savings_amount = 0
                upfront_cost = 0
                if 'EstimatedMonthlySavings' in rec:
                    savings_amount = float(rec['EstimatedMonthlySavings'].get('Amount', 0))
                if 'UpfrontCost' in rec:
                    upfront_cost = float(rec['UpfrontCost'].get('Amount', 0))
                
                instance_type = instance_details.get('InstanceType', 'unknown')
                region = instance_details.get('Region', 'unknown')
                
                recommendation = OptimizationRecommendation(
                    service='EC2',
                    resource_id=f"ri-{instance_type}-{region}",
                    resource_type='Reserved Instance',
                    recommendation_type='reserved_instance',
                    current_cost=upfront_cost,
                    estimated_savings=savings_amount,
                    confidence='HIGH',
                    description=f"Reserved Instance: {instance_type} in {region}",
                    remediation_steps=[
                        "Review the Reserved Instance recommendation details",
                        f"Purchase {rec.get('RecommendedNumberOfInstancesToPurchase', '1')} Reserved Instance(s)",
                        "Monitor RI utilization through AWS Cost Explorer",
                        "Consider setting up RI utilization alerts"
                    ],
                    region=region,
                    account_id=account_info.get('account_id', 'unknown'),
                    timestamp=datetime.now().isoformat(),
                    source='cost_explorer'
                )
                
                recommendations.append(recommendation)
                
        except Exception as e:
            handle_optimization_error(e, self.console)
            
        return recommendations
    
    async def get_billing_credits(self) -> Dict[str, Any]:
        """Get billing credits information"""
        try:
            session = aws_session.session
            billing_client = session.client('billing')
            
            # Get current month's credits
            end_date = datetime.now().date()
            start_date = end_date.replace(day=1)
            
            response = billing_client.list_credits(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                }
            )
            
            total_credits = 0
            credits_breakdown = []
            
            for credit in response.get('Credits', []):
                credit_amount = float(credit.get('Amount', {}).get('Amount', 0))
                total_credits += credit_amount
                
                credits_breakdown.append({
                    'type': credit.get('CreditType'),
                    'amount': credit_amount,
                    'currency': credit.get('Amount', {}).get('Unit', 'USD'),
                    'description': credit.get('Description', ''),
                    'expiry_date': credit.get('ExpiryDate')
                })
            
            return {
                'total_credits': total_credits,
                'currency': 'USD',
                'credits': credits_breakdown,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            handle_optimization_error(e, self.console)
            return {
                'total_credits': 0,
                'currency': 'USD',
                'credits': [],
                'error': str(e)
            }
    
    async def get_cost_optimization_hub_recommendations(self) -> List[OptimizationRecommendation]:
        """Get recommendations from Cost Optimization Hub"""
        recommendations = []
        
        try:
            session = aws_session.session
            coh_client = session.client('cost-optimization-hub')
            
            response = coh_client.list_recommendations(
                maxResults=100
            )
            
            # Get account info for recommendations
            account_info = await self.core.get_account_info()
            
            for rec in response.get('items', []):
                # Extract resource information properly
                resource_id = rec.get('resourceId', rec.get('recommendationId', 'unknown'))
                current_resource_type = rec.get('currentResourceType', 'unknown')
                recommended_resource_type = rec.get('recommendedResourceType', current_resource_type)
                action_type = rec.get('actionType', 'optimization')
                
                # Get resource name from tags or resource summary
                resource_name = self._extract_resource_name(rec)
                
                # Calculate savings and costs
                savings_amount = float(rec.get('estimatedMonthlySavings', 0))
                current_cost = float(rec.get('estimatedMonthlyCost', 0))
                
                # Determine confidence based on implementation effort
                confidence = self._map_implementation_effort_to_confidence(
                    rec.get('implementationEffort', 'Medium')
                )
                
                # Create meaningful description
                description = self._create_coh_description(rec, resource_name)
                
                # Create specific remediation steps
                remediation_steps = self._create_coh_remediation_steps(rec, resource_name)
                
                recommendation = OptimizationRecommendation(
                    service=self._map_resource_type_to_service(current_resource_type),
                    resource_id=resource_id,
                    resource_type=self._format_resource_type(current_resource_type),
                    recommendation_type=action_type,
                    current_cost=current_cost,
                    estimated_savings=savings_amount,
                    confidence=confidence,
                    description=description,
                    remediation_steps=remediation_steps,
                    region=rec.get('region', 'Global'),
                    account_id=rec.get('accountId', account_info.get('account_id', 'unknown')),
                    timestamp=rec.get('lastRefreshTimestamp', datetime.now().isoformat()),
                    source='cost_optimization_hub'
                )
                
                recommendations.append(recommendation)
                
        except Exception as e:
            handle_optimization_error(e, self.console)
            
        return recommendations
    
    def _extract_resource_name(self, rec: Dict[str, Any]) -> str:
        """Extract meaningful resource name from Cost Optimization Hub recommendation"""
        # Try to get name from tags first
        tags = rec.get('tags', [])
        for tag in tags:
            if tag.get('key', '').lower() == 'name':
                return tag.get('value', '')
        
        # Fall back to resource ID or summary
        resource_id = rec.get('resourceId', '')
        if resource_id and resource_id != 'unknown':
            return resource_id
        
        # Use current resource summary if available
        current_summary = rec.get('currentResourceSummary', '')
        if current_summary:
            return current_summary
        
        return 'Unknown Resource'
    
    def _map_implementation_effort_to_confidence(self, effort: str) -> str:
        """Map Cost Optimization Hub implementation effort to confidence level"""
        effort_mapping = {
            'VeryLow': 'HIGH',
            'Low': 'HIGH', 
            'Medium': 'MEDIUM',
            'High': 'MEDIUM',
            'VeryHigh': 'LOW'
        }
        return effort_mapping.get(effort, 'MEDIUM')
    
    def _map_resource_type_to_service(self, resource_type: str) -> str:
        """Map Cost Optimization Hub resource type to service name"""
        type_mapping = {
            'Ec2Instance': 'EC2',
            'Ec2AutoScalingGroup': 'Auto Scaling',
            'RdsDbInstance': 'RDS',
            'ComputeSavingsPlans': 'Savings Plans',
            'RdsReservedInstances': 'RDS Reserved Instances',
            'EbsVolume': 'EBS',
            'LambdaFunction': 'Lambda'
        }
        return type_mapping.get(resource_type, 'Cost Optimization Hub')
    
    def _format_resource_type(self, resource_type: str) -> str:
        """Format resource type for display"""
        type_mapping = {
            'Ec2Instance': 'EC2 Instance',
            'Ec2AutoScalingGroup': 'Auto Scaling Group',
            'RdsDbInstance': 'RDS Database',
            'ComputeSavingsPlans': 'Compute Savings Plan',
            'RdsReservedInstances': 'RDS Reserved Instance',
            'EbsVolume': 'EBS Volume',
            'LambdaFunction': 'Lambda Function'
        }
        return type_mapping.get(resource_type, resource_type)
    
    def _create_coh_description(self, rec: Dict[str, Any], resource_name: str) -> str:
        """Create meaningful description for Cost Optimization Hub recommendation"""
        action_type = rec.get('actionType', 'optimization')
        current_summary = rec.get('currentResourceSummary', '')
        recommended_summary = rec.get('recommendedResourceSummary', '')
        savings_percentage = rec.get('estimatedSavingsPercentage', 0)
        
        if action_type == 'MigrateToGraviton':
            return f"{resource_name}: Migrate from {current_summary} to {recommended_summary} (Graviton) - {savings_percentage}% savings"
        elif action_type == 'PurchaseSavingsPlans':
            return f"Purchase Compute Savings Plan: {recommended_summary} - {savings_percentage}% savings"
        elif action_type == 'PurchaseReservedInstances':
            return f"Purchase Reserved Instance: {recommended_summary} - {savings_percentage}% savings"
        elif action_type == 'Rightsize':
            return f"{resource_name}: Rightsize from {current_summary} to {recommended_summary} - {savings_percentage}% savings"
        else:
            return f"{resource_name}: {action_type} optimization - {savings_percentage}% savings"
    
    def _create_coh_remediation_steps(self, rec: Dict[str, Any], resource_name: str) -> List[str]:
        """Create specific remediation steps for Cost Optimization Hub recommendation"""
        action_type = rec.get('actionType', 'optimization')
        resource_type = rec.get('currentResourceType', '')
        implementation_effort = rec.get('implementationEffort', 'Medium')
        restart_needed = rec.get('restartNeeded', False)
        
        steps = []
        
        if action_type == 'MigrateToGraviton':
            steps = [
                f"Review current performance metrics for {resource_name}",
                f"Test workload compatibility with Graviton processors",
                f"Plan maintenance window for migration" + (" (restart required)" if restart_needed else ""),
                f"Update instance type to {rec.get('recommendedResourceSummary', 'Graviton-based')}",
                "Monitor performance and cost impact for 7-14 days"
            ]
        elif action_type == 'PurchaseSavingsPlans':
            steps = [
                "Review historical usage patterns to confirm commitment level",
                f"Purchase {rec.get('recommendedResourceSummary', 'Compute Savings Plan')}",
                "Set up billing alerts for Savings Plan utilization",
                "Monitor utilization monthly to ensure optimal coverage"
            ]
        elif action_type == 'PurchaseReservedInstances':
            steps = [
                "Analyze current usage patterns to confirm RI commitment",
                f"Purchase {rec.get('recommendedResourceSummary', 'Reserved Instance')}",
                "Set up RI utilization monitoring",
                "Review RI coverage quarterly for optimization opportunities"
            ]
        elif action_type == 'Rightsize':
            steps = [
                f"Analyze {resource_name} utilization over past 30 days",
                f"Test workload on {rec.get('recommendedResourceSummary', 'recommended size')}",
                f"Schedule maintenance window for resizing" + (" (restart required)" if restart_needed else ""),
                "Monitor performance after change for 48-72 hours"
            ]
        else:
            steps = [
                f"Review detailed recommendation for {resource_name} in AWS Cost Optimization Hub",
                f"Plan implementation considering {implementation_effort.lower()} effort level",
                "Implement the optimization during appropriate maintenance window",
                "Monitor cost and performance impact for 1-2 weeks"
            ]
        
        # Add effort level context
        if implementation_effort in ['High', 'VeryHigh']:
            steps.append(f"Note: This is a {implementation_effort.lower()} effort change - plan accordingly")
        
        return steps
    
    async def get_all_recommendations(self) -> List[OptimizationRecommendation]:
        """Get all Cost Explorer recommendations"""
        all_recommendations = []
        
        # Gather all recommendation types concurrently
        tasks = [
            self.get_rightsizing_recommendations(),
            self.get_savings_plans_recommendations(),
            self.get_reserved_instance_recommendations(),
            self.get_cost_optimization_hub_recommendations()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_recommendations.extend(result)
            elif isinstance(result, Exception):
                self.console.print(f"[yellow]Warning: {result}[/yellow]")
        
        return all_recommendations
    
    def create_spend_analysis_table(self, spend_data: Dict[str, Any]) -> Table:
        """Create a Rich table for spend analysis"""
        table = Table(title="Current Spend Analysis (Last 30 Days)")
        
        table.add_column("Service", style="cyan")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")
        
        total_cost = spend_data.get('total_cost', 0)
        
        for service in spend_data.get('services', []):
            percentage = (service['cost'] / total_cost * 100) if total_cost > 0 else 0
            table.add_row(
                service['service'],
                f"${service['cost']:.2f}",
                f"{percentage:.1f}%"
            )
        
        # Add total row
        table.add_row("", "", "", style="bold")
        table.add_row("TOTAL", f"${total_cost:.2f}", "100.0%", style="bold green")
        
        return table
    
    def create_recommendations_summary_table(self, recommendations: List[OptimizationRecommendation]) -> Table:
        """Create a summary table for Cost Explorer recommendations"""
        table = Table(title="Cost Explorer Optimization Summary")
        
        table.add_column("Recommendation Type", style="cyan")
        table.add_column("Resources", justify="right", style="blue")
        table.add_column("Est. Savings", justify="right", style="green")
        table.add_column("Avg Confidence", justify="center", style="yellow")
        
        # Group by recommendation type
        type_summary = {}
        for rec in recommendations:
            rec_type = rec.recommendation_type.replace('_', ' ').title()
            if rec_type not in type_summary:
                type_summary[rec_type] = {
                    'count': 0,
                    'total_savings': 0,
                    'confidences': []
                }
            
            type_summary[rec_type]['count'] += 1
            type_summary[rec_type]['total_savings'] += rec.estimated_savings
            type_summary[rec_type]['confidences'].append(rec.confidence)
        
        total_resources = 0
        total_savings = 0
        
        for rec_type, summary in type_summary.items():
            # Calculate average confidence
            confidence_scores = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            avg_confidence_score = sum(confidence_scores.get(c, 2) for c in summary['confidences']) / len(summary['confidences'])
            
            if avg_confidence_score >= 2.5:
                avg_confidence = 'HIGH'
            elif avg_confidence_score >= 1.5:
                avg_confidence = 'MEDIUM'
            else:
                avg_confidence = 'LOW'
            
            table.add_row(
                rec_type,
                str(summary['count']),
                f"${summary['total_savings']:.2f}",
                avg_confidence
            )
            
            total_resources += summary['count']
            total_savings += summary['total_savings']
        
        # Add total row
        if type_summary:
            table.add_row("", "", "", "", style="bold")
            table.add_row("TOTAL", str(total_resources), f"${total_savings:.2f}", "---", style="bold green")
        
        return table


# Create global instance for CLI integration
cost_explorer = CostExplorerIntegration()