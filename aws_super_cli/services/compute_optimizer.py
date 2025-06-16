"""
AWS Compute Optimizer Integration for Cost Optimization
Provides rightsizing recommendations and performance optimization suggestions for
EC2, EBS, Lambda, Auto Scaling Groups, and ECS services.
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


class ComputeOptimizerIntegration:
    """AWS Compute Optimizer integration for cost optimization recommendations"""
    
    def __init__(self, core: CostOptimizationCore = None):
        self.core = core or CostOptimizationCore()
        self.console = Console()
        
        # Compute Optimizer service types
        self.supported_services = {
            "ec2": "EC2 Instance",
            "ebs": "EBS Volume", 
            "lambda": "Lambda Function",
            "auto_scaling": "Auto Scaling Group",
            "ecs": "ECS Service"
        }
    
    async def check_enrollment_status(self) -> Dict[str, Any]:
        """Check Compute Optimizer enrollment status"""
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            response = compute_optimizer_client.get_enrollment_status()
            
            status = response.get('status', 'Unknown')
            status_reason = response.get('statusReason', '')
            member_accounts_enrolled = response.get('memberAccountsEnrolled', False)
            
            return {
                "enrolled": status == 'Active',
                "status": status,
                "status_reason": status_reason,
                "member_accounts_enrolled": member_accounts_enrolled,
                "message": f"Compute Optimizer status: {status}"
            }
            
        except Exception as e:
            error_message = str(e)
            
            # Check for common permission errors
            if 'AccessDenied' in error_message or 'UnauthorizedOperation' in error_message:
                return {
                    "enrolled": False,
                    "status": "Permission Denied",
                    "status_reason": "Missing ComputeOptimizerReadOnlyAccess policy",
                    "member_accounts_enrolled": False,
                    "message": "ComputeOptimizerReadOnlyAccess IAM policy required",
                    "error_code": "ACCESS_DENIED"
                }
            else:
                return {
                    "enrolled": False,
                    "status": "Error",
                    "status_reason": error_message,
                    "member_accounts_enrolled": False,
                    "message": f"Error checking Compute Optimizer status: {error_message}",
                    "error_code": "API_ERROR"
                }
    
    async def activate_enrollment(self) -> Dict[str, Any]:
        """Activate Compute Optimizer enrollment if not already active"""
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            # First check current status
            enrollment_status = await self.check_enrollment_status()
            
            if enrollment_status.get('enrolled'):
                return {
                    "success": True,
                    "message": "Compute Optimizer already enrolled",
                    "action": "none"
                }
            
            # Attempt to activate enrollment
            response = compute_optimizer_client.update_enrollment_status(
                status='Active',
                includeMemberAccounts=True
            )
            
            return {
                "success": True,
                "message": "Compute Optimizer enrollment activated successfully",
                "action": "activated",
                "response": response
            }
            
        except Exception as e:
            error_message = str(e)
            
            if 'AccessDenied' in error_message:
                return {
                    "success": False,
                    "message": "Permission denied - requires ComputeOptimizerFullAccess for enrollment",
                    "action": "failed",
                    "error_code": "ACCESS_DENIED"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to activate enrollment: {error_message}",
                    "action": "failed",
                    "error_code": "API_ERROR"
                }
    
    async def get_ec2_recommendations(self) -> List[OptimizationRecommendation]:
        """Get EC2 instance optimization recommendations"""
        recommendations = []
        
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            # Get account info
            account_info = await self.core.get_account_info()
            account_id = account_info.get('account_id', 'unknown')
            
            response = compute_optimizer_client.get_ec2_instance_recommendations()
            
            for rec in response.get('instanceRecommendations', []):
                instance_arn = rec.get('instanceArn', '')
                instance_name = rec.get('instanceName', '')
                current_instance_type = rec.get('currentInstanceType', '')
                finding = rec.get('finding', '')
                
                # Extract instance ID from ARN
                instance_id = instance_arn.split('/')[-1] if instance_arn else 'unknown'
                
                # Get recommendation options
                recommendation_options = rec.get('recommendationOptions', [])
                if recommendation_options:
                    best_option = recommendation_options[0]  # First option is usually best
                    recommended_type = best_option.get('instanceType', '')
                    
                    # Calculate estimated savings
                    estimated_monthly_savings = self._calculate_ec2_savings(
                        current_instance_type, recommended_type, finding
                    )
                    
                    # Determine confidence based on finding
                    confidence = self._get_confidence_from_finding(finding)
                    
                    recommendation = OptimizationRecommendation(
                        service="compute-optimizer",
                        resource_id=instance_id,
                        resource_type="EC2 Instance",
                        recommendation_type=f"Rightsizing - {finding}",
                        current_cost=0.0,  # Would need pricing API for exact cost
                        estimated_savings=estimated_monthly_savings,
                        confidence=confidence,
                        description=f"EC2 instance {finding.lower()}: {current_instance_type} → {recommended_type}",
                        remediation_steps=[
                            f"Review current utilization of {instance_id}",
                            f"Test workload on {recommended_type} instance type",
                            f"Schedule maintenance window for instance type change",
                            "Monitor performance after change"
                        ],
                        region=self._extract_region_from_arn(instance_arn),
                        account_id=account_id,
                        timestamp=datetime.now().isoformat(),
                        source="compute_optimizer"
                    )
                    
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not get EC2 recommendations: {e}[/yellow]")
            return []
    
    async def get_ebs_recommendations(self) -> List[OptimizationRecommendation]:
        """Get EBS volume optimization recommendations"""
        recommendations = []
        
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            # Get account info
            account_info = await self.core.get_account_info()
            account_id = account_info.get('account_id', 'unknown')
            
            response = compute_optimizer_client.get_ebs_volume_recommendations()
            
            for rec in response.get('volumeRecommendations', []):
                volume_arn = rec.get('volumeArn', '')
                current_config = rec.get('currentConfiguration', {})
                finding = rec.get('finding', '')
                
                # Extract volume ID from ARN
                volume_id = volume_arn.split('/')[-1] if volume_arn else 'unknown'
                
                current_volume_type = current_config.get('volumeType', '')
                current_volume_size = current_config.get('volumeSize', 0)
                
                # Get recommendation options
                recommendation_options = rec.get('volumeRecommendationOptions', [])
                if recommendation_options:
                    best_option = recommendation_options[0]
                    recommended_config = best_option.get('configuration', {})
                    recommended_type = recommended_config.get('volumeType', '')
                    recommended_size = recommended_config.get('volumeSize', 0)
                    
                    # Calculate estimated savings
                    estimated_monthly_savings = self._calculate_ebs_savings(
                        current_volume_type, current_volume_size,
                        recommended_type, recommended_size, finding
                    )
                    
                    confidence = self._get_confidence_from_finding(finding)
                    
                    recommendation = OptimizationRecommendation(
                        service="compute-optimizer",
                        resource_id=volume_id,
                        resource_type="EBS Volume",
                        recommendation_type=f"Volume Optimization - {finding}",
                        current_cost=0.0,
                        estimated_savings=estimated_monthly_savings,
                        confidence=confidence,
                        description=f"EBS volume {finding.lower()}: {current_volume_type} {current_volume_size}GB → {recommended_type} {recommended_size}GB",
                        remediation_steps=[
                            f"Review utilization patterns for volume {volume_id}",
                            "Create snapshot before modification",
                            f"Modify volume to {recommended_type} {recommended_size}GB",
                            "Monitor performance after change"
                        ],
                        region=self._extract_region_from_arn(volume_arn),
                        account_id=account_id,
                        timestamp=datetime.now().isoformat(),
                        source="compute_optimizer"
                    )
                    
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not get EBS recommendations: {e}[/yellow]")
            return []
    
    async def get_lambda_recommendations(self) -> List[OptimizationRecommendation]:
        """Get Lambda function optimization recommendations"""
        recommendations = []
        
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            # Get account info
            account_info = await self.core.get_account_info()
            account_id = account_info.get('account_id', 'unknown')
            
            response = compute_optimizer_client.get_lambda_function_recommendations()
            
            for rec in response.get('lambdaFunctionRecommendations', []):
                function_arn = rec.get('functionArn', '')
                function_version = rec.get('functionVersion', '')
                current_config = rec.get('currentMemorySize', 0)
                finding = rec.get('finding', '')
                
                # Extract function name from ARN
                function_name = function_arn.split(':')[-1] if function_arn else 'unknown'
                
                # Get recommendation options
                recommendation_options = rec.get('memorySizeRecommendationOptions', [])
                if recommendation_options:
                    best_option = recommendation_options[0]
                    recommended_memory = best_option.get('memorySize', 0)
                    
                    # Calculate estimated savings
                    estimated_monthly_savings = self._calculate_lambda_savings(
                        current_config, recommended_memory, finding
                    )
                    
                    confidence = self._get_confidence_from_finding(finding)
                    
                    recommendation = OptimizationRecommendation(
                        service="compute-optimizer",
                        resource_id=function_name,
                        resource_type="Lambda Function",
                        recommendation_type=f"Memory Optimization - {finding}",
                        current_cost=0.0,
                        estimated_savings=estimated_monthly_savings,
                        confidence=confidence,
                        description=f"Lambda function {finding.lower()}: {current_config}MB → {recommended_memory}MB",
                        remediation_steps=[
                            f"Review performance metrics for {function_name}",
                            f"Test function with {recommended_memory}MB memory",
                            "Update function configuration",
                            "Monitor execution time and cost after change"
                        ],
                        region=self._extract_region_from_arn(function_arn),
                        account_id=account_id,
                        timestamp=datetime.now().isoformat(),
                        source="compute_optimizer"
                    )
                    
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not get Lambda recommendations: {e}[/yellow]")
            return []
    
    async def get_auto_scaling_recommendations(self) -> List[OptimizationRecommendation]:
        """Get Auto Scaling Group optimization recommendations"""
        recommendations = []
        
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            # Get account info
            account_info = await self.core.get_account_info()
            account_id = account_info.get('account_id', 'unknown')
            
            response = compute_optimizer_client.get_auto_scaling_group_recommendations()
            
            for rec in response.get('autoScalingGroupRecommendations', []):
                asg_arn = rec.get('autoScalingGroupArn', '')
                asg_name = rec.get('autoScalingGroupName', '')
                current_config = rec.get('currentConfiguration', {})
                finding = rec.get('finding', '')
                
                current_instance_type = current_config.get('instanceType', '')
                
                # Get recommendation options
                recommendation_options = rec.get('recommendationOptions', [])
                if recommendation_options:
                    best_option = recommendation_options[0]
                    recommended_config = best_option.get('configuration', {})
                    recommended_instance_type = recommended_config.get('instanceType', '')
                    
                    # Calculate estimated savings
                    estimated_monthly_savings = self._calculate_asg_savings(
                        current_instance_type, recommended_instance_type, finding
                    )
                    
                    confidence = self._get_confidence_from_finding(finding)
                    
                    recommendation = OptimizationRecommendation(
                        service="compute-optimizer",
                        resource_id=asg_name,
                        resource_type="Auto Scaling Group",
                        recommendation_type=f"ASG Optimization - {finding}",
                        current_cost=0.0,
                        estimated_savings=estimated_monthly_savings,
                        confidence=confidence,
                        description=f"Auto Scaling Group {finding.lower()}: {current_instance_type} → {recommended_instance_type}",
                        remediation_steps=[
                            f"Review ASG utilization patterns for {asg_name}",
                            f"Create new launch template with {recommended_instance_type}",
                            "Update Auto Scaling Group configuration",
                            "Monitor performance and scaling behavior"
                        ],
                        region=self._extract_region_from_arn(asg_arn),
                        account_id=account_id,
                        timestamp=datetime.now().isoformat(),
                        source="compute_optimizer"
                    )
                    
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not get Auto Scaling Group recommendations: {e}[/yellow]")
            return []
    
    async def get_ecs_recommendations(self) -> List[OptimizationRecommendation]:
        """Get ECS service optimization recommendations"""
        recommendations = []
        
        try:
            session = aws_session.session
            compute_optimizer_client = session.client('compute-optimizer', region_name='us-east-1')
            
            # Get account info
            account_info = await self.core.get_account_info()
            account_id = account_info.get('account_id', 'unknown')
            
            response = compute_optimizer_client.get_ecs_service_recommendations()
            
            for rec in response.get('ecsServiceRecommendations', []):
                service_arn = rec.get('serviceArn', '')
                current_config = rec.get('currentServiceConfiguration', {})
                finding = rec.get('finding', '')
                
                # Extract service name from ARN
                service_name = service_arn.split('/')[-1] if service_arn else 'unknown'
                
                current_cpu = current_config.get('cpu', 0)
                current_memory = current_config.get('memory', 0)
                
                # Get recommendation options
                recommendation_options = rec.get('serviceRecommendationOptions', [])
                if recommendation_options:
                    best_option = recommendation_options[0]
                    recommended_config = best_option.get('containerRecommendations', [])
                    
                    if recommended_config:
                        container_rec = recommended_config[0]
                        recommended_cpu = container_rec.get('cpu', 0)
                        recommended_memory = container_rec.get('memory', 0)
                        
                        # Calculate estimated savings
                        estimated_monthly_savings = self._calculate_ecs_savings(
                            current_cpu, current_memory,
                            recommended_cpu, recommended_memory, finding
                        )
                        
                        confidence = self._get_confidence_from_finding(finding)
                        
                        recommendation = OptimizationRecommendation(
                            service="compute-optimizer",
                            resource_id=service_name,
                            resource_type="ECS Service",
                            recommendation_type=f"ECS Optimization - {finding}",
                            current_cost=0.0,
                            estimated_savings=estimated_monthly_savings,
                            confidence=confidence,
                            description=f"ECS service {finding.lower()}: {current_cpu}CPU/{current_memory}MB → {recommended_cpu}CPU/{recommended_memory}MB",
                            remediation_steps=[
                                f"Review ECS service utilization for {service_name}",
                                f"Update task definition with {recommended_cpu}CPU/{recommended_memory}MB",
                                "Deploy new task definition",
                                "Monitor service performance and scaling"
                            ],
                            region=self._extract_region_from_arn(service_arn),
                            account_id=account_id,
                            timestamp=datetime.now().isoformat(),
                            source="compute_optimizer"
                        )
                        
                        recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not get ECS recommendations: {e}[/yellow]")
            return []
    
    async def get_all_recommendations(self) -> List[OptimizationRecommendation]:
        """Get all Compute Optimizer recommendations across all services"""
        all_recommendations = []
        
        # Check enrollment status first
        enrollment_status = await self.check_enrollment_status()
        if not enrollment_status.get('enrolled'):
            if enrollment_status.get('error_code') == 'ACCESS_DENIED':
                raise OptimizationError(
                    message=enrollment_status.get('message'),
                    error_code=enrollment_status.get('error_code'),
                    remediation="Attach ComputeOptimizerReadOnlyAccess IAM policy to your user/role"
                )
            else:
                # Try to activate enrollment
                activation_result = await self.activate_enrollment()
                if not activation_result.get('success'):
                    raise OptimizationError(
                        message=f"Compute Optimizer not enrolled: {enrollment_status.get('status_reason')}",
                        error_code="NOT_ENROLLED",
                        remediation="Enable Compute Optimizer in AWS Console or ensure proper IAM permissions"
                    )
        
        # Get recommendations from all services
        self.console.print("[dim]Gathering Compute Optimizer recommendations...[/dim]")
        
        # Run all recommendation gathering in parallel for better performance
        ec2_task = self.get_ec2_recommendations()
        ebs_task = self.get_ebs_recommendations()
        lambda_task = self.get_lambda_recommendations()
        asg_task = self.get_auto_scaling_recommendations()
        ecs_task = self.get_ecs_recommendations()
        
        results = await asyncio.gather(
            ec2_task, ebs_task, lambda_task, asg_task, ecs_task,
            return_exceptions=True
        )
        
        # Collect all successful results
        for result in results:
            if isinstance(result, list):
                all_recommendations.extend(result)
            elif isinstance(result, Exception):
                self.console.print(f"[yellow]Warning: {result}[/yellow]")
        
        return all_recommendations
    
    def _calculate_ec2_savings(self, current_type: str, recommended_type: str, finding: str) -> float:
        """Calculate estimated monthly savings for EC2 instance type change"""
        # Simplified savings calculation based on finding type
        if finding == 'Underprovisioned':
            return 0.0  # No savings, performance improvement
        elif finding == 'Overprovisioned':
            return 150.0  # Estimated monthly savings
        elif finding == 'Optimized':
            return 0.0  # Already optimized
        else:
            return 75.0  # Default moderate savings
    
    def _calculate_ebs_savings(self, current_type: str, current_size: int, 
                              recommended_type: str, recommended_size: int, finding: str) -> float:
        """Calculate estimated monthly savings for EBS volume optimization"""
        if finding == 'Underprovisioned':
            return 0.0
        elif finding == 'Overprovisioned':
            size_diff = current_size - recommended_size
            return max(0, size_diff * 0.10)  # $0.10 per GB per month (approximate)
        else:
            return 20.0  # Default EBS savings
    
    def _calculate_lambda_savings(self, current_memory: int, recommended_memory: int, finding: str) -> float:
        """Calculate estimated monthly savings for Lambda memory optimization"""
        if finding == 'Underprovisioned':
            return 0.0
        elif finding == 'Overprovisioned':
            memory_diff = current_memory - recommended_memory
            return max(0, memory_diff * 0.001)  # Approximate Lambda pricing
        else:
            return 10.0  # Default Lambda savings
    
    def _calculate_asg_savings(self, current_type: str, recommended_type: str, finding: str) -> float:
        """Calculate estimated monthly savings for Auto Scaling Group optimization"""
        if finding == 'Underprovisioned':
            return 0.0
        elif finding == 'Overprovisioned':
            return 200.0  # Estimated savings for ASG optimization
        else:
            return 100.0  # Default ASG savings
    
    def _calculate_ecs_savings(self, current_cpu: int, current_memory: int,
                              recommended_cpu: int, recommended_memory: int, finding: str) -> float:
        """Calculate estimated monthly savings for ECS service optimization"""
        if finding == 'Underprovisioned':
            return 0.0
        elif finding == 'Overprovisioned':
            cpu_diff = current_cpu - recommended_cpu
            memory_diff = current_memory - recommended_memory
            return max(0, (cpu_diff * 0.04) + (memory_diff * 0.004))  # Fargate pricing approximation
        else:
            return 30.0  # Default ECS savings
    
    def _get_confidence_from_finding(self, finding: str) -> str:
        """Map Compute Optimizer finding to confidence level"""
        if finding in ['Overprovisioned', 'Underprovisioned']:
            return 'HIGH'
        elif finding == 'Optimized':
            return 'LOW'  # No change needed
        else:
            return 'MEDIUM'
    
    def _extract_region_from_arn(self, arn: str) -> str:
        """Extract AWS region from ARN"""
        try:
            parts = arn.split(':')
            return parts[3] if len(parts) > 3 else 'unknown'
        except:
            return 'unknown'
    
    def create_compute_optimizer_summary_table(self, recommendations: List[OptimizationRecommendation]) -> Table:
        """Create a summary table of Compute Optimizer recommendations"""
        table = Table(title="Compute Optimizer Cost Optimization Summary")
        table.add_column("Service Type", style="cyan")
        table.add_column("Resources", style="yellow")
        table.add_column("Est. Savings", style="bold green")
        table.add_column("Avg Confidence", style="magenta")
        
        # Group recommendations by resource type
        grouped = {}
        for rec in recommendations:
            resource_type = rec.resource_type
            if resource_type not in grouped:
                grouped[resource_type] = {
                    "count": 0,
                    "total_savings": 0.0,
                    "confidences": []
                }
            grouped[resource_type]["count"] += 1
            grouped[resource_type]["total_savings"] += rec.estimated_savings
            grouped[resource_type]["confidences"].append(rec.confidence)
        
        # Add rows to table
        total_savings = 0.0
        for resource_type, data in grouped.items():
            # Calculate average confidence
            confidences = data["confidences"]
            high_count = confidences.count("HIGH")
            medium_count = confidences.count("MEDIUM")
            low_count = confidences.count("LOW")
            
            if high_count >= medium_count and high_count >= low_count:
                avg_confidence = "HIGH"
            elif medium_count >= low_count:
                avg_confidence = "MEDIUM"
            else:
                avg_confidence = "LOW"
            
            table.add_row(
                resource_type,
                str(data["count"]),
                f"${data['total_savings']:.2f}",
                avg_confidence
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
compute_optimizer = ComputeOptimizerIntegration()