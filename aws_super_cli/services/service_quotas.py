"""AWS Service Quotas Integration for proactive quota monitoring and optimization."""

import boto3
from typing import Dict, List, Optional, Any
from datetime import datetime
from rich.table import Table
from rich.console import Console
from .cost_optimization import OptimizationRecommendation


class ServiceQuotasIntegration:
    """AWS Service Quotas integration for proactive quota monitoring."""
    
    def __init__(self, aws_session):
        """Initialize Service Quotas integration."""
        self.aws_session = aws_session
        self.console = Console()
        
    async def get_quota_recommendations(self) -> List[OptimizationRecommendation]:
        """Get quota utilization analysis and recommendations."""
        try:
            recommendations = []
            
            # Get quota utilization data
            quota_data = await self._get_quota_utilization()
            
            # Analyze quotas approaching limits
            for quota in quota_data:
                if quota['utilization_percentage'] >= 80:  # 80% threshold
                    recommendation = self._create_quota_recommendation(quota)
                    if recommendation:
                        recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.console.print(f"Error getting Service Quotas recommendations: {str(e)}")
            return []
    
    async def _get_quota_utilization(self) -> List[Dict[str, Any]]:
        """Get quota utilization data from Service Quotas API."""
        try:
            quotas_client = self.aws_session.session.client('service-quotas')
            cloudwatch_client = self.aws_session.session.client('cloudwatch')
            
            quota_data = []
            
            # Get list of services with quotas
            services_response = quotas_client.list_services()
            
            for service in services_response.get('Services', [])[:10]:  # Limit to top 10 services
                service_code = service['ServiceCode']
                service_name = service['ServiceName']
                
                try:
                    # Get quotas for this service
                    quotas_response = quotas_client.list_service_quotas(ServiceCode=service_code)
                    
                    for quota in quotas_response.get('Quotas', [])[:5]:  # Top 5 quotas per service
                        quota_info = await self._analyze_quota_utilization(
                            quota, service_code, service_name, cloudwatch_client
                        )
                        if quota_info:
                            quota_data.append(quota_info)
                            
                except Exception as service_error:
                    # Skip services that don't support quotas or have permission issues
                    continue
            
            return quota_data
            
        except Exception as e:
            self.console.print(f"Error fetching quota data: {str(e)}")
            return []
    
    async def _analyze_quota_utilization(self, quota: Dict, service_code: str, 
                                       service_name: str, cloudwatch_client) -> Optional[Dict[str, Any]]:
        """Analyze individual quota utilization."""
        try:
            quota_name = quota.get('QuotaName', 'Unknown')
            quota_value = quota.get('Value', 0)
            quota_arn = quota.get('QuotaArn', '')
            
            # Try to get current usage from CloudWatch
            current_usage = await self._get_quota_usage_from_cloudwatch(
                service_code, quota_name, cloudwatch_client
            )
            
            if current_usage is None:
                # Estimate usage based on service (simplified approach)
                current_usage = await self._estimate_quota_usage(service_code, quota_name)
            
            if current_usage is not None and quota_value > 0:
                utilization_percentage = (current_usage / quota_value) * 100
                
                return {
                    'service_code': service_code,
                    'service_name': service_name,
                    'quota_name': quota_name,
                    'quota_arn': quota_arn,
                    'quota_value': quota_value,
                    'current_usage': current_usage,
                    'utilization_percentage': utilization_percentage,
                    'available_capacity': quota_value - current_usage
                }
            
            return None
            
        except Exception as e:
            return None
    
    async def _get_quota_usage_from_cloudwatch(self, service_code: str, quota_name: str, 
                                             cloudwatch_client) -> Optional[float]:
        """Get quota usage from CloudWatch metrics."""
        try:
            # Map service codes to CloudWatch metrics (simplified mapping)
            metric_mappings = {
                'ec2': {
                    'Running On-Demand EC2 Instances': {
                        'namespace': 'AWS/EC2',
                        'metric_name': 'RunningInstances'
                    }
                },
                'rds': {
                    'DB instances': {
                        'namespace': 'AWS/RDS',
                        'metric_name': 'DatabaseConnections'
                    }
                },
                'lambda': {
                    'Concurrent executions': {
                        'namespace': 'AWS/Lambda',
                        'metric_name': 'ConcurrentExecutions'
                    }
                }
            }
            
            if service_code in metric_mappings and quota_name in metric_mappings[service_code]:
                metric_info = metric_mappings[service_code][quota_name]
                
                # Get recent metric data
                response = cloudwatch_client.get_metric_statistics(
                    Namespace=metric_info['namespace'],
                    MetricName=metric_info['metric_name'],
                    StartTime=datetime.utcnow().replace(hour=0, minute=0, second=0),
                    EndTime=datetime.utcnow(),
                    Period=3600,  # 1 hour
                    Statistics=['Maximum']
                )
                
                if response.get('Datapoints'):
                    return max(dp['Maximum'] for dp in response['Datapoints'])
            
            return None
            
        except Exception:
            return None
    
    async def _estimate_quota_usage(self, service_code: str, quota_name: str) -> Optional[float]:
        """Estimate quota usage based on service resources (simplified)."""
        try:
            # Simple estimation based on resource counts
            if service_code == 'ec2' and 'instances' in quota_name.lower():
                ec2_client = self.aws_session.session.client('ec2')
                response = ec2_client.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
                )
                return len([i for r in response['Reservations'] for i in r['Instances']])
            
            elif service_code == 'rds' and 'instances' in quota_name.lower():
                rds_client = self.aws_session.session.client('rds')
                response = rds_client.describe_db_instances()
                return len(response.get('DBInstances', []))
            
            elif service_code == 's3' and 'buckets' in quota_name.lower():
                s3_client = self.aws_session.session.client('s3')
                response = s3_client.list_buckets()
                return len(response.get('Buckets', []))
            
            return None
            
        except Exception:
            return None
    
    def _create_quota_recommendation(self, quota: Dict[str, Any]) -> Optional[OptimizationRecommendation]:
        """Create optimization recommendation for quota approaching limit."""
        try:
            utilization = quota['utilization_percentage']
            service_name = quota['service_name']
            quota_name = quota['quota_name']
            current_usage = quota['current_usage']
            quota_value = quota['quota_value']
            available_capacity = quota['available_capacity']
            
            # Determine urgency and recommendation
            if utilization >= 95:
                urgency = "Critical"
                description = f"CRITICAL: {quota_name} is at {utilization:.1f}% capacity ({current_usage}/{quota_value})"
            elif utilization >= 90:
                urgency = "High"
                description = f"HIGH: {quota_name} is at {utilization:.1f}% capacity ({current_usage}/{quota_value})"
            else:
                urgency = "Medium"
                description = f"MEDIUM: {quota_name} is at {utilization:.1f}% capacity ({current_usage}/{quota_value})"
            
            # Calculate recommended increase
            recommended_increase = max(quota_value * 0.5, available_capacity * 2)  # 50% increase or 2x available
            
            remediation_steps = [
                f"Request quota increase for {quota_name}",
                f"Current limit: {quota_value}, Recommended: {quota_value + recommended_increase}",
                f"Submit quota increase request via AWS Service Quotas console",
                f"Monitor usage trends to prevent future quota exhaustion",
                "Consider resource optimization to reduce quota pressure"
            ]
            
            return OptimizationRecommendation(
                service="service-quotas",
                resource_id=quota.get('quota_arn', f"{quota['service_code']}/{quota_name}"),
                resource_type="quota",
                recommendation_type="quota_increase",
                current_cost=0.0,  # Quotas don't have direct cost
                estimated_savings=0.0,  # Preventive measure
                confidence=urgency,
                description=description,
                remediation_steps=remediation_steps,
                region="global",
                account_id=self.aws_session.account_id or "unknown",
                timestamp=datetime.utcnow().isoformat(),
                source="service-quotas"
            )
            
        except Exception as e:
            self.console.print(f"Error creating quota recommendation: {str(e)}")
            return None
    
    def create_quota_utilization_table(self, quota_data: List[Dict[str, Any]]) -> Table:
        """Create Rich table for quota utilization display."""
        table = Table(title="Service Quotas Utilization Analysis")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Quota Name", style="blue")
        table.add_column("Usage", justify="right", style="yellow")
        table.add_column("Limit", justify="right", style="green")
        table.add_column("Utilization", justify="right", style="red")
        table.add_column("Available", justify="right", style="green")
        table.add_column("Status", justify="center")
        
        for quota in quota_data:
            utilization = quota['utilization_percentage']
            
            # Status indicator
            if utilization >= 95:
                status = "🔴 Critical"
            elif utilization >= 90:
                status = "🟠 High"
            elif utilization >= 80:
                status = "🟡 Medium"
            else:
                status = "🟢 OK"
            
            table.add_row(
                quota['service_name'][:20],
                quota['quota_name'][:30],
                f"{quota['current_usage']:.0f}",
                f"{quota['quota_value']:.0f}",
                f"{utilization:.1f}%",
                f"{quota['available_capacity']:.0f}",
                status
            )
        
        return table
    
    def create_quota_recommendations_table(self, recommendations: List[OptimizationRecommendation]) -> Table:
        """Create Rich table for quota recommendations."""
        table = Table(title="Service Quotas Recommendations")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Quota", style="blue")
        table.add_column("Urgency", justify="center", style="red")
        table.add_column("Description", style="yellow")
        table.add_column("Action Required", style="green")
        
        for rec in recommendations:
            # Extract service name from resource_id
            service_name = rec.resource_id.split('/')[0] if '/' in rec.resource_id else rec.service
            quota_name = rec.resource_id.split('/')[-1] if '/' in rec.resource_id else "Unknown"
            
            # Get first remediation step as action
            action = rec.remediation_steps[0] if rec.remediation_steps else "Review quota usage"
            
            table.add_row(
                service_name[:15],
                quota_name[:25],
                rec.confidence,
                rec.description[:50] + "..." if len(rec.description) > 50 else rec.description,
                action[:40] + "..." if len(action) > 40 else action
            )
        
        return table 