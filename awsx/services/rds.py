"""RDS service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_rds_data(instances_by_region: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format RDS instance data for display"""
    formatted_instances = []
    
    for region, response in instances_by_region.items():
        if not response or 'DBInstances' not in response:
            continue
            
        for instance in response['DBInstances']:
            # Format creation date
            created = instance.get('InstanceCreateTime')
            if created:
                created_str = created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)
            else:
                created_str = 'N/A'
            
            # Get master username
            master_username = instance.get('MasterUsername', 'N/A')
            
            # Get storage info
            allocated_storage = instance.get('AllocatedStorage', 0)
            storage_type = instance.get('StorageType', 'N/A')
            storage_info = f"{allocated_storage}GB ({storage_type})" if allocated_storage else 'N/A'
            
            # Get VPC info
            vpc_id = 'N/A'
            if instance.get('DBSubnetGroup'):
                vpc_id = instance['DBSubnetGroup'].get('VpcId', 'N/A')
            
            formatted_instances.append({
                'DB Instance ID': instance['DBInstanceIdentifier'],
                'Engine': f"{instance.get('Engine', 'N/A')} {instance.get('EngineVersion', '')}".strip(),
                'Status': instance.get('DBInstanceStatus', 'N/A'),
                'Class': instance.get('DBInstanceClass', 'N/A'),
                'Storage': storage_info,
                'Master User': master_username,
                'VPC': vpc_id,
                'Multi-AZ': '✓' if instance.get('MultiAZ', False) else '',
                'Public': '✓' if instance.get('PubliclyAccessible', False) else '',
                'Region': region,
                'AZ': instance.get('AvailabilityZone', 'N/A'),
                'Created': created_str,
                'Endpoint': instance.get('Endpoint', {}).get('Address', 'N/A') if instance.get('Endpoint') else 'N/A'
            })
    
    return formatted_instances


def create_rds_table(instances: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for RDS instances"""
    if not columns:
        columns = ['DB Instance ID', 'Engine', 'Status', 'Class', 'Storage', 'Region']
    
    table = Table(title="RDS Instances", show_header=True, header_style="bold magenta")
    
    # Add columns with appropriate styling
    for col in columns:
        if col in ['DB Instance ID']:
            table.add_column(col, style="cyan", min_width=15)
        elif col == 'Status':
            table.add_column(col, style="green", min_width=10)
        elif col == 'Engine':
            table.add_column(col, style="blue", min_width=12)
        elif col in ['Multi-AZ', 'Public']:
            table.add_column(col, style="yellow", min_width=8)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for instance in instances:
        row = []
        for col in columns:
            value = instance.get(col, 'N/A')
            # Color code statuses
            if col == 'Status':
                if value == 'available':
                    value = f"[green]{value}[/green]"
                elif value in ['creating', 'modifying', 'starting', 'stopping']:
                    value = f"[yellow]{value}[/yellow]"
                elif value in ['stopped', 'failed', 'incompatible-parameters']:
                    value = f"[red]{value}[/red]"
            elif col in ['Multi-AZ', 'Public'] and value == '✓':
                value = f"[yellow]{value}[/yellow]"
            row.append(value)
        table.add_row(*row)
    
    return table


async def list_rds_instances(
    regions: List[str] = None,
    all_regions: bool = False,
    match: str = None,
    engine: str = None
) -> List[Dict[str, str]]:
    """List RDS instances across regions with optional filters"""
    
    # Determine regions to query
    if regions:
        # User specified specific regions - use those
        pass
    elif all_regions:
        # User wants all regions (default behavior)
        regions = aws_session.get_available_regions('rds')
    else:
        # User wants current region only (--no-all-regions)
        try:
            import boto3
            session = boto3.Session()
            current_region = session.region_name or 'us-east-1'
            regions = [current_region]
        except:
            regions = ['us-east-1']
    
    # Build filters - RDS doesn't support complex filters like EC2, so we'll filter post-query
    kwargs = {}
    
    # Make async calls
    responses = await aws_session.call_service_async(
        'rds', 
        'describe_db_instances',
        regions=regions,
        **kwargs
    )
    
    # Format the data
    instances = format_rds_data(responses)
    
    # Apply engine filter
    if engine:
        engine_lower = engine.lower()
        filtered_instances = []
        for instance in instances:
            if engine_lower in instance['Engine'].lower():
                filtered_instances.append(instance)
        instances = filtered_instances
    
    # Apply match filter (fuzzy search on instance ID and engine)
    if match:
        match_lower = match.lower()
        filtered_instances = []
        for instance in instances:
            # Check if match is in instance ID, engine, or VPC
            searchable_text = f"{instance['DB Instance ID']} {instance['Engine']} {instance['VPC']}".lower()
            if match_lower in searchable_text:
                filtered_instances.append(instance)
        instances = filtered_instances
    
    return instances 