"""ARN Intelligence - Smart ARN handling and display utilities"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ARNComponents:
    """Parsed ARN components"""
    arn: str
    partition: str
    service: str
    region: str
    account_id: str
    resource_type: str
    resource_id: str
    resource_path: Optional[str] = None


class ARNIntelligence:
    """Smart ARN processing and display utilities"""
    
    # Service-specific display preferences
    SERVICE_DISPLAY_RULES = {
        'iam': {
            'show_resource_type': False,  # Skip "user/" or "role/"
            'preferred_length': 25,
            'highlight_part': 'resource_id'
        },
        's3': {
            'show_resource_type': False,  # Just show bucket name
            'preferred_length': 30,
            'highlight_part': 'resource_id'
        },
        'ec2': {
            'show_resource_type': True,   # Show "instance/", "volume/", etc.
            'preferred_length': 20,
            'highlight_part': 'resource_id'
        },
        'lambda': {
            'show_resource_type': False,  # Skip "function:"
            'preferred_length': 25,
            'highlight_part': 'resource_id'
        },
        'rds': {
            'show_resource_type': True,   # Show "db:", "cluster:", etc.
            'preferred_length': 25,
            'highlight_part': 'resource_id'
        }
    }
    
    def __init__(self):
        self.arn_pattern = re.compile(
            r'arn:(?P<partition>[^:]+):(?P<service>[^:]+):(?P<region>[^:]*):(?P<account>[^:]*):(?P<resource>.*)'
        )
    
    def parse_arn(self, arn: str) -> Optional[ARNComponents]:
        """Parse an ARN string into components"""
        if not arn or not arn.startswith('arn:'):
            return None
        
        match = self.arn_pattern.match(arn)
        if not match:
            return None
        
        groups = match.groupdict()
        resource = groups['resource']
        
        # Parse resource part - can be "type/id" or "type:id" or just "id"
        resource_type = ""
        resource_id = resource
        resource_path = None
        
        # Handle "type/id" format
        if '/' in resource:
            parts = resource.split('/', 1)
            resource_type = parts[0]
            remaining = parts[1]
            
            # Check for additional path components
            if '/' in remaining:
                path_parts = remaining.split('/')
                resource_id = path_parts[0]
                resource_path = '/'.join(path_parts[1:])
            else:
                resource_id = remaining
        
        # Handle "type:id" format
        elif ':' in resource:
            parts = resource.split(':', 1)
            resource_type = parts[0]
            resource_id = parts[1]
        
        return ARNComponents(
            arn=arn,
            partition=groups['partition'],
            service=groups['service'],
            region=groups['region'],
            account_id=groups['account'],
            resource_type=resource_type,
            resource_id=resource_id,
            resource_path=resource_path
        )
    
    def get_human_readable_name(self, arn: str) -> str:
        """Get a human-readable name from an ARN"""
        components = self.parse_arn(arn)
        if not components:
            return arn
        
        service_rules = self.SERVICE_DISPLAY_RULES.get(
            components.service, 
            {'show_resource_type': True, 'preferred_length': 30, 'highlight_part': 'resource_id'}
        )
        
        # Build the display name
        if service_rules['show_resource_type'] and components.resource_type:
            display_name = f"{components.resource_type}/{components.resource_id}"
        else:
            display_name = components.resource_id
        
        return display_name
    
    def smart_truncate(self, arn: str, max_length: int = None) -> str:
        """Intelligently truncate an ARN for display"""
        components = self.parse_arn(arn)
        if not components:
            return arn[:max_length-3] + "..." if max_length and len(arn) > max_length else arn
        
        # Get service-specific rules
        service_rules = self.SERVICE_DISPLAY_RULES.get(components.service, {})
        preferred_length = max_length or service_rules.get('preferred_length', 30)
        
        # Get human readable name first
        human_name = self.get_human_readable_name(arn)
        
        # If it fits, return it
        if len(human_name) <= preferred_length:
            return human_name
        
        # If it doesn't fit, truncate intelligently
        if preferred_length <= 10:
            return human_name[:preferred_length-3] + "..."
        
        # Try to keep the end (usually the ID) and show "..." at start
        if len(human_name) > preferred_length:
            keep_length = preferred_length - 3
            return "..." + human_name[-keep_length:]
        
        return human_name
    
    def explain_arn(self, arn: str) -> Dict[str, str]:
        """Provide a detailed explanation of an ARN"""
        components = self.parse_arn(arn)
        if not components:
            return {"error": "Invalid ARN format"}
        
        explanation = {
            "ARN": arn,
            "Partition": f"{components.partition} (AWS partition)",
            "Service": f"{components.service} ({self._get_service_description(components.service)})",
            "Region": f"{components.region or 'Global'} ({self._get_region_description(components.region)})",
            "Account": f"{components.account_id} (AWS Account ID)",
            "Resource Type": f"{components.resource_type or 'N/A'} ({self._get_resource_type_description(components.service, components.resource_type)})",
            "Resource ID": f"{components.resource_id} (Unique identifier)",
        }
        
        if components.resource_path:
            explanation["Resource Path"] = f"{components.resource_path} (Additional path components)"
        
        return explanation
    
    def _get_service_description(self, service: str) -> str:
        """Get a human description of an AWS service"""
        service_descriptions = {
            'iam': 'Identity and Access Management',
            'ec2': 'Elastic Compute Cloud',
            's3': 'Simple Storage Service',
            'lambda': 'AWS Lambda Functions',
            'rds': 'Relational Database Service',
            'vpc': 'Virtual Private Cloud',
            'elbv2': 'Elastic Load Balancing v2',
            'elasticloadbalancing': 'Elastic Load Balancing',
            'route53': 'Route 53 DNS Service',
            'cloudformation': 'CloudFormation Infrastructure',
            'sns': 'Simple Notification Service',
            'sqs': 'Simple Queue Service',
            'kms': 'Key Management Service',
            'secretsmanager': 'Secrets Manager',
            'ssm': 'Systems Manager',
            'logs': 'CloudWatch Logs',
            'cloudwatch': 'CloudWatch Monitoring',
            'events': 'EventBridge Rules',
            'dynamodb': 'DynamoDB NoSQL Database'
        }
        return service_descriptions.get(service, f'{service.upper()} Service')
    
    def _get_region_description(self, region: str) -> str:
        """Get a human description of an AWS region"""
        if not region:
            return "Global service"
        
        region_descriptions = {
            'us-east-1': 'N. Virginia',
            'us-east-2': 'Ohio', 
            'us-west-1': 'N. California',
            'us-west-2': 'Oregon',
            'eu-west-1': 'Ireland',
            'eu-west-2': 'London',
            'eu-west-3': 'Paris',
            'eu-central-1': 'Frankfurt',
            'ap-southeast-1': 'Singapore',
            'ap-southeast-2': 'Sydney',
            'ap-northeast-1': 'Tokyo',
            'ap-south-1': 'Mumbai',
            'sa-east-1': 'São Paulo',
            'ca-central-1': 'Canada Central'
        }
        return region_descriptions.get(region, f'{region} region')
    
    def _get_resource_type_description(self, service: str, resource_type: str) -> str:
        """Get a human description of a resource type"""
        if not resource_type:
            return "Direct resource"
        
        type_descriptions = {
            'iam': {
                'user': 'IAM User',
                'role': 'IAM Role', 
                'policy': 'IAM Policy',
                'group': 'IAM Group'
            },
            'ec2': {
                'instance': 'EC2 Instance',
                'volume': 'EBS Volume',
                'snapshot': 'EBS Snapshot',
                'security-group': 'Security Group',
                'vpc': 'Virtual Private Cloud',
                'subnet': 'VPC Subnet',
                'internet-gateway': 'Internet Gateway',
                'route-table': 'Route Table',
                'image': 'AMI Image'
            },
            's3': {
                'bucket': 'S3 Bucket',
                'object': 'S3 Object'
            },
            'lambda': {
                'function': 'Lambda Function',
                'layer': 'Lambda Layer'
            },
            'rds': {
                'db': 'RDS Database Instance',
                'cluster': 'RDS Aurora Cluster',
                'snapshot': 'RDS Snapshot'
            }
        }
        
        service_types = type_descriptions.get(service, {})
        return service_types.get(resource_type, f'{resource_type} resource')
    
    def format_arn_for_display(self, arn: str, show_full: bool = False, max_length: int = None) -> str:
        """Format an ARN for display based on context"""
        if show_full:
            return arn
        
        return self.smart_truncate(arn, max_length)
    
    def get_arn_pattern_matches(self, arns: List[str], pattern: str) -> List[str]:
        """Find ARNs that match a given pattern"""
        if not pattern:
            return arns
        
        pattern_lower = pattern.lower()
        matches = []
        
        for arn in arns:
            components = self.parse_arn(arn)
            if not components:
                continue
            
            # Check if pattern matches any component
            searchable_text = ' '.join([
                components.service,
                components.region or '',
                components.resource_type or '',
                components.resource_id,
                self.get_human_readable_name(arn)
            ]).lower()
            
            if pattern_lower in searchable_text:
                matches.append(arn)
        
        return matches


# Global instance for easy access
arn_intelligence = ARNIntelligence() 