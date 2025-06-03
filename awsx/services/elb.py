"""ELB/ALB service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_elb_data(elbs_by_region: Dict[str, Any], albs_by_region: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format ELB and ALB data for display"""
    formatted_lbs = []
    
    # Process Classic Load Balancers (ELB)
    for region, response in elbs_by_region.items():
        if not response or 'LoadBalancerDescriptions' not in response:
            continue
            
        for elb in response['LoadBalancerDescriptions']:
            # Format creation date
            created = elb.get('CreatedTime')
            if created:
                created_str = created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)
            else:
                created_str = 'N/A'
            
            # Get instance count
            instance_count = len(elb.get('Instances', []))
            
            # Get AZ count and VPC
            azs = elb.get('AvailabilityZones', [])
            vpc_id = elb.get('VPCId', 'EC2-Classic')
            
            formatted_lbs.append({
                'Name': elb['LoadBalancerName'],
                'Type': 'Classic',
                'State': 'N/A',  # Classic ELBs don't have state
                'Scheme': elb.get('Scheme', 'N/A'),
                'VPC': vpc_id,
                'AZs': f"{len(azs)} zones",
                'Instances': str(instance_count),
                'DNS Name': elb.get('DNSName', 'N/A'),
                'Region': region,
                'Created': created_str
            })
    
    # Process Application/Network Load Balancers (ALB/NLB)
    for region, response in albs_by_region.items():
        if not response or 'LoadBalancers' not in response:
            continue
            
        for alb in response['LoadBalancers']:
            # Format creation date
            created = alb.get('CreatedTime')
            if created:
                created_str = created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)
            else:
                created_str = 'N/A'
            
            # Get AZ count
            azs = alb.get('AvailabilityZones', [])
            vpc_id = alb.get('VpcId', 'N/A')
            
            formatted_lbs.append({
                'Name': alb['LoadBalancerName'],
                'Type': alb.get('Type', 'application').title(),
                'State': alb.get('State', {}).get('Code', 'N/A'),
                'Scheme': alb.get('Scheme', 'N/A'),
                'VPC': vpc_id,
                'AZs': f"{len(azs)} zones",
                'Instances': 'N/A',  # ALB targets are in target groups, not directly attached
                'DNS Name': alb.get('DNSName', 'N/A'),
                'Region': region,
                'Created': created_str
            })
    
    return formatted_lbs


def create_elb_table(load_balancers: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for load balancers"""
    if not columns:
        columns = ['Name', 'Type', 'State', 'Scheme', 'VPC', 'AZs', 'Region']
    
    table = Table(title="Load Balancers", show_header=True, header_style="bold magenta")
    
    # Add columns with appropriate styling
    for col in columns:
        if col == 'Name':
            table.add_column(col, style="cyan", min_width=20)
        elif col == 'State':
            table.add_column(col, style="green", min_width=10)
        elif col == 'Type':
            table.add_column(col, style="blue", min_width=12)
        elif col == 'Scheme':
            table.add_column(col, style="yellow", min_width=10)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for lb in load_balancers:
        row = []
        for col in columns:
            value = lb.get(col, 'N/A')
            # Color code states
            if col == 'State':
                if value == 'active':
                    value = f"[green]{value}[/green]"
                elif value in ['provisioning', 'active_impaired']:
                    value = f"[yellow]{value}[/yellow]"
                elif value == 'failed':
                    value = f"[red]{value}[/red]"
            elif col == 'Type':
                if value == 'Classic':
                    value = f"[dim]{value}[/dim]"
                else:
                    value = f"[blue]{value}[/blue]"
            row.append(value)
        table.add_row(*row)
    
    return table


async def list_load_balancers(
    regions: List[str] = None,
    all_regions: bool = False,
    match: str = None,
    lb_type: str = None
) -> List[Dict[str, str]]:
    """List load balancers across regions with optional filters"""
    
    # Determine regions to query
    if regions:
        # User specified specific regions - use those
        pass
    elif all_regions:
        # User wants all regions (default behavior)
        regions = aws_session.get_available_regions('elb')
    else:
        # User wants current region only (--no-all-regions)
        try:
            import boto3
            session = boto3.Session()
            current_region = session.region_name or 'us-east-1'
            regions = [current_region]
        except:
            regions = ['us-east-1']
    
    # Make async calls for both Classic ELBs and ALBs/NLBs
    elb_responses = await aws_session.call_service_async(
        'elb', 
        'describe_load_balancers',
        regions=regions
    )
    
    alb_responses = await aws_session.call_service_async(
        'elbv2', 
        'describe_load_balancers',
        regions=regions
    )
    
    # Format the data
    load_balancers = format_elb_data(elb_responses, alb_responses)
    
    # Apply type filter
    if lb_type:
        lb_type_lower = lb_type.lower()
        filtered_lbs = []
        for lb in load_balancers:
            if lb_type_lower in lb['Type'].lower():
                filtered_lbs.append(lb)
        load_balancers = filtered_lbs
    
    # Apply match filter (fuzzy search on name, type, and VPC)
    if match:
        match_lower = match.lower()
        filtered_lbs = []
        for lb in load_balancers:
            # Check if match is in name, type, or VPC
            searchable_text = f"{lb['Name']} {lb['Type']} {lb['VPC']}".lower()
            if match_lower in searchable_text:
                filtered_lbs.append(lb)
        load_balancers = filtered_lbs
    
    return load_balancers 