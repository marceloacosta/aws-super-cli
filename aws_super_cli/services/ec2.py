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
    
    # Check if this is multi-account data by looking for Account field
    is_multi_account = any('Account' in instance for instance in instances)
    
    if not columns:
        if is_multi_account:
            columns = ['Instance ID', 'Name', 'State', 'Type', 'Account', 'Region']
        else:
            columns = ['Instance ID', 'Name', 'State', 'Type', 'Region']
    
    table = Table(title="EC2 Instances", show_header=True, header_style="bold magenta")
    
    # Add columns with appropriate styling
    for col in columns:
        if col == 'Instance ID':
            table.add_column(col, style="cyan", min_width=15)
        elif col == 'State':
            table.add_column(col, style="green", min_width=10)
        elif col == 'Type':
            table.add_column(col, style="blue", min_width=12)
        elif col == 'Account':
            table.add_column(col, style="yellow", min_width=12)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for instance in instances:
        row = []
        for col in columns:
            value = instance.get(col, 'N/A')
            # Color code states
            if col == 'State':
                if value == 'running':
                    value = f"[green]{value}[/green]"
                elif value in ['starting', 'stopping', 'rebooting']:
                    value = f"[yellow]{value}[/yellow]"
                elif value in ['stopped', 'terminated']:
                    value = f"[red]{value}[/red]"
            elif col == 'Account' and len(value) == 12:
                # Highlight account IDs
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
    if regions:
        # User specified specific regions - use those
        pass
    elif all_regions:
        # User wants all regions (default behavior)
        regions = aws_session.get_available_regions('ec2')
    else:
        # User wants current region only (--no-all-regions)
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


def format_ec2_data_multi_account(responses_by_account: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format EC2 data from multiple accounts for display"""
    formatted_instances = []
    
    # Extract metadata if present
    metadata = responses_by_account.pop('metadata', {})
    
    for key, response in responses_by_account.items():
        if not response or 'Reservations' not in response:
            continue
        
        # Get account and region info from metadata or key
        account_info = metadata.get(key, {})
        account_id = account_info.get('account_id', key.split(':')[0] if ':' in key else 'Unknown')
        region = account_info.get('region', key.split(':')[1] if ':' in key else 'Unknown')
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # Get instance name from tags
                name = 'N/A'
                tags_list = []
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                    tags_list.append(f"{tag['Key']}={tag['Value']}")
                
                # Format launch time
                launch_time = instance.get('LaunchTime')
                if launch_time:
                    launch_str = launch_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(launch_time, 'strftime') else str(launch_time)
                else:
                    launch_str = 'N/A'
                
                # Get VPC info
                vpc_id = instance.get('VpcId', 'EC2-Classic')
                
                formatted_instances.append({
                    'Instance ID': instance['InstanceId'],
                    'Name': name,
                    'State': instance['State']['Name'],
                    'Type': instance.get('InstanceType', 'N/A'),
                    'Private IP': instance.get('PrivateIpAddress', 'N/A'),
                    'Public IP': instance.get('PublicIpAddress', 'N/A'),
                    'VPC': vpc_id,
                    'Region': region,
                    'Account': account_id,  # Add account column for multi-account
                    'AZ': instance.get('Placement', {}).get('AvailabilityZone', 'N/A'),
                    'Launch Time': launch_str,
                    'Tags': '; '.join(tags_list) if tags_list else 'N/A'
                })
    
    return formatted_instances


def apply_ec2_filters(instances: List[Dict[str, str]], match: str = None, state: str = None, 
                     instance_type: str = None, tag: str = None) -> List[Dict[str, str]]:
    """Apply filters to EC2 instances"""
    filtered = instances.copy()
    
    # Apply state filter
    if state:
        state_lower = state.lower()
        filtered = [inst for inst in filtered if state_lower in inst['State'].lower()]
    
    # Apply instance type filter
    if instance_type:
        type_lower = instance_type.lower()
        filtered = [inst for inst in filtered if type_lower in inst['Type'].lower()]
    
    # Apply tag filter (format: key=value)
    if tag and '=' in tag:
        key, value = tag.split('=', 1)
        key_lower = key.lower()
        value_lower = value.lower()
        
        def tag_matches(instance_tags: str) -> bool:
            if instance_tags == 'N/A':
                return False
            for tag_pair in instance_tags.split('; '):
                if '=' in tag_pair:
                    tag_key, tag_value = tag_pair.split('=', 1)
                    if key_lower in tag_key.lower() and value_lower in tag_value.lower():
                        return True
            return False
        
        filtered = [inst for inst in filtered if tag_matches(inst['Tags'])]
    
    # Apply match filter (fuzzy search across multiple fields)
    if match:
        match_lower = match.lower()
        
        def matches_instance(instance: Dict[str, str]) -> bool:
            searchable_fields = [
                instance['Instance ID'], instance['Name'], instance['Type'],
                instance['VPC'], instance['Tags'], instance.get('Account', '')
            ]
            searchable_text = ' '.join(str(field) for field in searchable_fields).lower()
            return match_lower in searchable_text
        
        filtered = [inst for inst in filtered if matches_instance(inst)]
    
    return filtered 