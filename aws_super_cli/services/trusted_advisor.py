"""
AWS Trusted Advisor Integration for Cost Optimization
Provides cost-saving recommendations from AWS Trusted Advisor including idle resources,
under-utilized storage, and discount suggestions.
"""

import asyncio
from datetime import datetime
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


class TrustedAdvisorIntegration:
    """AWS Trusted Advisor integration for cost optimization recommendations"""
    
    def __init__(self, core: CostOptimizationCore = None):
        self.core = core or CostOptimizationCore()
        self.console = Console()
        
        # Trusted Advisor check categories for cost optimization
        self.cost_optimization_checks = {
            "cost_optimizing": [
                "Low Utilization Amazon EC2 Instances",
                "Idle Load Balancers", 
                "Unassociated Elastic IP Addresses",
                "Underutilized Amazon EBS Volumes",
                "Amazon RDS Idle DB Instances",
                "Amazon Route 53 Latency Resource Record Sets",
                "Large Number of Rules in an EC2 Security Group",
                "Large Number of EC2 Security Group Rules Applied to an Instance"
            ],
            "service_limits": [
                "Service Limits"
            ],
            "fault_tolerance": [
                "Amazon EBS Snapshots",
                "Amazon EC2 Availability Zone Balance"
            ]
        }
    
    async def check_support_plan_access(self) -> Dict[str, Any]:
        """Check if current account has access to Trusted Advisor"""
        try:
            session = aws_session.session
            support_client = session.client('support', region_name='us-east-1')
            
            # Try to get Trusted Advisor checks
            try:
                response = support_client.describe_trusted_advisor_checks(language='en')
                
                return {
                    "has_access": True,
                    "support_plan": "Business/Enterprise",
                    "checks_available": len(response.get('checks', [])),
                    "message": "Trusted Advisor access confirmed"
                }
                
            except Exception as api_error:
                # Check if it's a subscription-related error
                error_code = getattr(api_error, 'response', {}).get('Error', {}).get('Code', '')
                error_message = str(api_error)
                
                if 'SubscriptionRequired' in error_code or 'subscription' in error_message.lower():
                    return {
                        "has_access": False,
                        "support_plan": "Basic/Developer",
                        "checks_available": 0,
                        "message": "Business or Enterprise support plan required for Trusted Advisor",
                        "error_code": "SUBSCRIPTION_REQUIRED"
                    }
                else:
                    # Re-raise for general error handling
                    raise api_error
                
        except Exception as e:
            return {
                "has_access": False,
                "support_plan": "Unknown",
                "checks_available": 0,
                "message": f"Error checking Trusted Advisor access: {e}",
                "error_code": "ACCESS_ERROR"
            }
    
    async def get_available_checks(self) -> List[Dict[str, Any]]:
        """Get all available Trusted Advisor checks"""
        try:
            session = aws_session.session
            support_client = session.client('support', region_name='us-east-1')
            
            response = support_client.describe_trusted_advisor_checks(language='en')
            
            checks = []
            for check in response.get('checks', []):
                checks.append({
                    "id": check.get('id'),
                    "name": check.get('name'),
                    "description": check.get('description'),
                    "category": check.get('category'),
                    "metadata": check.get('metadata', [])
                })
            
            return checks
            
        except Exception as e:
            self.console.print(f"[red]Error getting Trusted Advisor checks: {e}[/red]")
            return []
    
    async def get_cost_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Get cost optimization recommendations from Trusted Advisor"""
        recommendations = []
        
        try:
            # First check if we have access
            access_check = await self.check_support_plan_access()
            if not access_check.get('has_access'):
                raise OptimizationError(
                    message=access_check.get('message'),
                    error_code=access_check.get('error_code'),
                    remediation="Upgrade to Business or Enterprise support plan to access Trusted Advisor"
                )
            
            # Get account info
            account_info = await self.core.get_account_info()
            account_id = account_info.get('account_id', 'unknown')
            
            session = aws_session.session
            support_client = session.client('support', region_name='us-east-1')
            
            # Get all available checks
            checks_response = support_client.describe_trusted_advisor_checks(language='en')
            
            # Filter for cost optimization checks
            cost_checks = []
            for check in checks_response.get('checks', []):
                check_name = check.get('name', '')
                for category, check_names in self.cost_optimization_checks.items():
                    if any(cost_check in check_name for cost_check in check_names):
                        cost_checks.append(check)
                        break
            
            self.console.print(f"[dim]Found {len(cost_checks)} cost optimization checks[/dim]")
            
            # Get check results for each cost optimization check
            for check in cost_checks:
                check_id = check.get('id')
                check_name = check.get('name')
                
                try:
                    # Get check result
                    result_response = support_client.describe_trusted_advisor_check_result(
                        checkId=check_id,
                        language='en'
                    )
                    
                    result = result_response.get('result', {})
                    status = result.get('status')
                    
                    # Only process checks with findings (warning or error status)
                    if status in ['warning', 'error']:
                        flagged_resources = result.get('flaggedResources', [])
                        
                        for resource in flagged_resources:
                            recommendation = self._create_recommendation_from_resource(
                                check, resource, account_id
                            )
                            if recommendation:
                                recommendations.append(recommendation)
                
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not get results for check '{check_name}': {e}[/yellow]")
                    continue
            
            self.console.print(f"[green]Generated {len(recommendations)} cost optimization recommendations[/green]")
            return recommendations
            
        except OptimizationError:
            raise
        except Exception as e:
            raise OptimizationError(
                message=f"Error getting Trusted Advisor recommendations: {e}",
                error_code="TRUSTED_ADVISOR_ERROR",
                remediation="Check AWS credentials and Trusted Advisor permissions"
            )
    
    def _create_recommendation_from_resource(self, check: Dict, resource: Dict, 
                                           account_id: str) -> Optional[OptimizationRecommendation]:
        """Create an OptimizationRecommendation from a Trusted Advisor flagged resource"""
        try:
            check_name = check.get('name', 'Unknown Check')
            metadata = resource.get('metadata', [])
            
            # Extract resource information based on check type
            resource_id = "unknown"
            resource_type = "Unknown"
            current_cost = 0.0
            estimated_savings = 0.0
            region = "unknown"
            confidence = "MEDIUM"
            description = check_name
            remediation_steps = []
            
            # Parse different types of Trusted Advisor checks
            if "EC2 Instances" in check_name:
                resource_type = "EC2 Instance"
                if len(metadata) > 0:
                    resource_id = metadata[0] if metadata[0] else "unknown"
                if len(metadata) > 1:
                    region = metadata[1] if metadata[1] else "unknown"
                if len(metadata) > 3:
                    try:
                        estimated_savings = float(metadata[3].replace('$', '').replace(',', ''))
                    except (ValueError, AttributeError):
                        estimated_savings = 0.0
                
                description = f"Low utilization EC2 instance detected"
                remediation_steps = [
                    "Review instance utilization metrics",
                    "Consider stopping or terminating if not needed",
                    "Resize to smaller instance type if appropriate",
                    "Consider Reserved Instances for consistent workloads"
                ]
                confidence = "HIGH"
                
            elif "Load Balancers" in check_name:
                resource_type = "Load Balancer"
                if len(metadata) > 0:
                    resource_id = metadata[0] if metadata[0] else "unknown"
                if len(metadata) > 1:
                    region = metadata[1] if metadata[1] else "unknown"
                
                description = f"Idle load balancer detected"
                remediation_steps = [
                    "Check if load balancer is still needed",
                    "Remove if no longer in use",
                    "Consolidate multiple load balancers if possible"
                ]
                estimated_savings = 25.0  # Approximate monthly cost
                confidence = "HIGH"
                
            elif "Elastic IP" in check_name:
                resource_type = "Elastic IP"
                if len(metadata) > 0:
                    resource_id = metadata[0] if metadata[0] else "unknown"
                if len(metadata) > 1:
                    region = metadata[1] if metadata[1] else "unknown"
                
                description = f"Unassociated Elastic IP address"
                remediation_steps = [
                    "Associate with an EC2 instance if needed",
                    "Release if no longer required"
                ]
                estimated_savings = 3.65  # $0.005/hour * 24 * 30
                confidence = "HIGH"
                
            elif "EBS Volumes" in check_name:
                resource_type = "EBS Volume"
                if len(metadata) > 0:
                    resource_id = metadata[0] if metadata[0] else "unknown"
                if len(metadata) > 1:
                    region = metadata[1] if metadata[1] else "unknown"
                if len(metadata) > 3:
                    try:
                        estimated_savings = float(metadata[3].replace('$', '').replace(',', ''))
                    except (ValueError, AttributeError):
                        estimated_savings = 0.0
                
                description = f"Underutilized EBS volume detected"
                remediation_steps = [
                    "Analyze volume usage patterns",
                    "Consider resizing to smaller volume",
                    "Migrate to cheaper storage class if appropriate",
                    "Delete if no longer needed"
                ]
                confidence = "MEDIUM"
                
            elif "RDS" in check_name:
                resource_type = "RDS Instance"
                if len(metadata) > 0:
                    resource_id = metadata[0] if metadata[0] else "unknown"
                if len(metadata) > 1:
                    region = metadata[1] if metadata[1] else "unknown"
                
                description = f"Idle RDS database instance detected"
                remediation_steps = [
                    "Review database connection metrics",
                    "Stop or terminate if not in use",
                    "Consider Aurora Serverless for variable workloads"
                ]
                estimated_savings = 50.0  # Approximate monthly cost
                confidence = "HIGH"
            
            else:
                # Generic handling for other check types
                if len(metadata) > 0:
                    resource_id = metadata[0] if metadata[0] else "unknown"
                description = f"Cost optimization opportunity: {check_name}"
                remediation_steps = ["Review resource usage and optimize as needed"]
            
            return OptimizationRecommendation(
                service="trusted-advisor",
                resource_id=resource_id,
                resource_type=resource_type,
                recommendation_type=check_name,
                current_cost=current_cost,
                estimated_savings=estimated_savings,
                confidence=confidence,
                description=description,
                remediation_steps=remediation_steps,
                region=region,
                account_id=account_id,
                timestamp=datetime.now().isoformat(),
                source="trusted_advisor"
            )
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not parse resource from {check.get('name', 'unknown')}: {e}[/yellow]")
            return None
    
    def create_trusted_advisor_summary_table(self, recommendations: List[OptimizationRecommendation]) -> Table:
        """Create a summary table of Trusted Advisor recommendations"""
        table = Table(title="Trusted Advisor Cost Optimization Summary")
        table.add_column("Check Type", style="cyan")
        table.add_column("Resources", style="yellow")
        table.add_column("Est. Savings", style="bold green")
        table.add_column("Confidence", style="magenta")
        
        # Group recommendations by type
        grouped = {}
        for rec in recommendations:
            check_type = rec.recommendation_type
            if check_type not in grouped:
                grouped[check_type] = {
                    "count": 0,
                    "total_savings": 0.0,
                    "confidence": rec.confidence
                }
            grouped[check_type]["count"] += 1
            grouped[check_type]["total_savings"] += rec.estimated_savings
        
        # Add rows to table
        total_savings = 0.0
        for check_type, data in grouped.items():
            table.add_row(
                check_type,
                str(data["count"]),
                f"${data['total_savings']:.2f}",
                data["confidence"]
            )
            total_savings += data["total_savings"]
        
        # Add total row
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{len(recommendations)}[/bold]",
            f"[bold]${total_savings:.2f}[/bold]",
            "[bold]---[/bold]"
        )
        
        return table


# Global instance for easy access
trusted_advisor = TrustedAdvisorIntegration() 