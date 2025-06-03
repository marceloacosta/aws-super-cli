"""EC2 service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def shorten_arn(arn: str, max_length: int = 30) -> str:
    """Shorten ARN for display purposes"""
    if len(arn) <= max_length:
        return arn
    # Take the resource part of the ARN (after the last :)
    parts = arn.split(':')
    if len(parts) > 1:
        resource = parts[-1]
        if len(resource) <= max_length - 3:
            return f"...{resource}"
    return f"{arn[:max_length-3]}..."


def format_instance_data(instances_by_region: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format EC2 instance data for display"""
    formatted_instances = []
    
    for region, response in instances_by_region.items():
        if not response or 'Reservations' not in response:
            continue
            
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # Extract instance name from tags
                name = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                # Format tags for display
                tags = []
                for tag in instance.get('Tags', []):
                    if tag['Key'] != 'Name':
                        tags.append(f"{tag['Key']}={tag['Value']}")
                tags_str = ', '.join(tags[:2])  # Show first 2 tags
                if len(instance.get('Tags', [])) > 3:  # Name + 2 others
                    tags_str += '...'
                
                formatted_instances.append({
                    'Instance ID': instance['InstanceId'],
                    'Name': name,
                    'State': instance['State']['Name'],
                    'Type': instance['InstanceType'],
                    'Region': region,
                    'AZ': instance['Placement']['AvailabilityZone'],
                    'Private IP': instance.get('PrivateIpAddress', 'N/A'),
                    'Public IP': instance.get('PublicIpAddress', 'N/A'),
                    'Tags': tags_str or 'N/A'
                })
    
    return formatted_instances


def create_ec2_table(instances: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for EC2 instances"""
    if not columns:
        columns = ['Instance ID', 'Name', 'State', 'Type', 'Region', 'AZ']
    
    table = Table(title="EC2 Instances", show_header=True, header_style="bold magenta")
    
    # Add columns
    for col in columns:
        if col in ['Instance ID', 'Name']:
            table.add_column(col, style="cyan", min_width=10)
        elif col == 'State':
            table.add_column(col, style="green", min_width=8)
        else:
            table.add_column(col, min_width=8)
    
    # Add rows
    for instance in instances:
        row = []
        for col in columns:
            value = instance.get(col, 'N/A')
            # Color code states
            if col == 'State':
                if value == 'running':
                    value = f"[green]{value}[/green]"
                elif value == 'stopped':
                    value = f"[red]{value}[/red]"
                elif value in ['pending', 'stopping', 'starting']:
                    value = f"[yellow]{value}[/yellow]"
            row.append(value)
        table.add_row(*row)
    
    return table


async def list_ec2_instances(
    regions: List[str] = None,
    all_regions: bool = False,
    match: str = None,
    state: str = None,
    tag_filters: Dict[str, str] = None
) -> List[Dict[str, str]]:
    """List EC2 instances across regions with optional filters"""
    
    # Determine regions to query
    if all_regions:
        regions = aws_session.get_available_regions('ec2')
    elif not regions:
        # Default to current region (try to detect from session)
        try:
            import boto3
            session = boto3.Session()
            current_region = session.region_name or 'us-east-1'
            regions = [current_region]
        except:
            regions = ['us-east-1']
    
    # Build filters
    filters = []
    if state:
        filters.append({'Name': 'instance-state-name', 'Values': [state]})
    
    if tag_filters:
        for key, value in tag_filters.items():
            filters.append({'Name': f'tag:{key}', 'Values': [value]})
    
    # Make async calls
    kwargs = {}
    if filters:
        kwargs['Filters'] = filters
    
    responses = await aws_session.call_service_async(
        'ec2', 
        'describe_instances',
        regions=regions,
        **kwargs
    )
    
    # Format the data
    instances = format_instance_data(responses)
    
    # Apply match filter (fuzzy search on name and tags)
    if match:
        match_lower = match.lower()
        filtered_instances = []
        for instance in instances:
            # Check if match is in name, instance ID, or tags
            searchable_text = f"{instance['Name']} {instance['Instance ID']} {instance['Tags']}".lower()
            if match_lower in searchable_text:
                filtered_instances.append(instance)
        instances = filtered_instances
    
    return instances 