"""VPC service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_vpc_data(vpcs_by_region: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format VPC data for display"""
    formatted_vpcs = []
    
    for region, response in vpcs_by_region.items():
        if not response or 'Vpcs' not in response:
            continue
            
        for vpc in response['Vpcs']:
            # Extract VPC name from tags
            name = 'N/A'
            for tag in vpc.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break
            
            # Format tags for display (exclude Name)
            tags = []
            for tag in vpc.get('Tags', []):
                if tag['Key'] != 'Name':
                    tags.append(f"{tag['Key']}={tag['Value']}")
            tags_str = ', '.join(tags[:2])  # Show first 2 tags
            if len(vpc.get('Tags', [])) > 3:  # Name + 2 others
                tags_str += '...'
            
            # Determine if it's the default VPC
            is_default = '✓' if vpc.get('IsDefault', False) else ''
            
            formatted_vpcs.append({
                'VPC ID': vpc['VpcId'],
                'Name': name,
                'CIDR': vpc['CidrBlock'],
                'State': vpc['State'],
                'Default': is_default,
                'Region': region,
                'Tenancy': vpc.get('InstanceTenancy', 'default'),
                'Tags': tags_str or 'N/A'
            })
    
    return formatted_vpcs


def create_vpc_table(vpcs: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for VPCs"""
    if not columns:
        columns = ['VPC ID', 'Name', 'CIDR', 'State', 'Default', 'Region']
    
    table = Table(title="VPCs", show_header=True, header_style="bold magenta")
    
    # Add columns
    for col in columns:
        if col in ['VPC ID', 'Name']:
            table.add_column(col, style="cyan", min_width=12)
        elif col == 'State':
            table.add_column(col, style="green", min_width=10)
        elif col == 'CIDR':
            table.add_column(col, style="blue", min_width=12)
        elif col == 'Default':
            table.add_column(col, style="yellow", min_width=8)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for vpc in vpcs:
        row = []
        for col in columns:
            value = vpc.get(col, 'N/A')
            # Color code states
            if col == 'State':
                if value == 'available':
                    value = f"[green]{value}[/green]"
                elif value == 'pending':
                    value = f"[yellow]{value}[/yellow]"
                else:
                    value = f"[red]{value}[/red]"
            elif col == 'Default' and value == '✓':
                value = f"[yellow]{value}[/yellow]"
            row.append(value)
        table.add_row(*row)
    
    return table


async def list_vpcs(
    regions: List[str] = None,
    all_regions: bool = False,
    match: str = None,
    tag_filters: Dict[str, str] = None
) -> List[Dict[str, str]]:
    """List VPCs across regions with optional filters"""
    
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
    if tag_filters:
        for key, value in tag_filters.items():
            filters.append({'Name': f'tag:{key}', 'Values': [value]})
    
    # Make async calls
    kwargs = {}
    if filters:
        kwargs['Filters'] = filters
    
    responses = await aws_session.call_service_async(
        'ec2', 
        'describe_vpcs',
        regions=regions,
        **kwargs
    )
    
    # Format the data
    vpcs = format_vpc_data(responses)
    
    # Apply match filter (fuzzy search on name, VPC ID, and tags)
    if match:
        match_lower = match.lower()
        filtered_vpcs = []
        for vpc in vpcs:
            # Check if match is in name, VPC ID, or tags
            searchable_text = f"{vpc['Name']} {vpc['VPC ID']} {vpc['Tags']}".lower()
            if match_lower in searchable_text:
                filtered_vpcs.append(vpc)
        vpcs = filtered_vpcs
    
    return vpcs 