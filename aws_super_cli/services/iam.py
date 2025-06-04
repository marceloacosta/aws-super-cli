"""IAM service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_iam_data(users_response: Dict[str, Any], roles_response: Dict[str, Any], resource_type: str = 'all') -> List[Dict[str, str]]:
    """Format IAM data for display"""
    formatted_resources = []
    
    # Process IAM Users
    if resource_type in ['all', 'users'] and users_response:
        for region, response in users_response.items():
            if not response or 'Users' not in response:
                continue
                
            for user in response['Users']:
                # Format creation date
                created = user.get('CreateDate')
                if created:
                    created_str = created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)
                else:
                    created_str = 'N/A'
                
                # Get last activity (password last used)
                last_activity = user.get('PasswordLastUsed')
                if last_activity:
                    last_activity_str = last_activity.strftime('%Y-%m-%d %H:%M:%S') if hasattr(last_activity, 'strftime') else str(last_activity)
                else:
                    last_activity_str = 'Never'
                
                formatted_resources.append({
                    'Name': user['UserName'],
                    'Type': 'User',
                    'Status': 'N/A',
                    'ARN': user.get('Arn', 'N/A'),
                    'Path': user.get('Path', '/'),
                    'Created': created_str,
                    'Last Activity': last_activity_str,
                    'Max Session Duration': 'N/A'
                })
    
    # Process IAM Roles
    if resource_type in ['all', 'roles'] and roles_response:
        for region, response in roles_response.items():
            if not response or 'Roles' not in response:
                continue
                
            for role in response['Roles']:
                # Format creation date
                created = role.get('CreateDate')
                if created:
                    created_str = created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)
                else:
                    created_str = 'N/A'
                
                # Get max session duration
                max_session = role.get('MaxSessionDuration', 3600)
                max_session_str = f"{max_session//3600}h {(max_session%3600)//60}m" if max_session >= 3600 else f"{max_session//60}m"
                
                formatted_resources.append({
                    'Name': role['RoleName'],
                    'Type': 'Role',
                    'Status': 'N/A',
                    'ARN': role.get('Arn', 'N/A'),
                    'Path': role.get('Path', '/'),
                    'Created': created_str,
                    'Last Activity': 'N/A',
                    'Max Session Duration': max_session_str
                })
    
    return formatted_resources


def create_iam_table(resources: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for IAM resources"""
    if not columns:
        columns = ['Name', 'Type', 'Path', 'Created', 'Last Activity']
    
    table = Table(title="IAM Resources", show_header=True, header_style="bold magenta")
    
    # Add columns with appropriate styling
    for col in columns:
        if col == 'Name':
            table.add_column(col, style="cyan", min_width=20)
        elif col == 'Type':
            table.add_column(col, style="blue", min_width=8)
        elif col == 'Path':
            table.add_column(col, style="dim", min_width=8)
        elif col == 'Last Activity':
            table.add_column(col, style="yellow", min_width=12)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for resource in resources:
        row = []
        for col in columns:
            value = resource.get(col, 'N/A')
            # Color code types and activities
            if col == 'Type':
                if value == 'User':
                    value = f"[blue]{value}[/blue]"
                elif value == 'Role':
                    value = f"[green]{value}[/green]"
            elif col == 'Last Activity':
                if value == 'Never':
                    value = f"[red]{value}[/red]"
                elif value != 'N/A':
                    # Check if it's recent (within 30 days - simplified check)
                    if '2024' in value or '2025' in value:  # Simplified recent check
                        value = f"[green]{value}[/green]"
                    else:
                        value = f"[yellow]{value}[/yellow]"
            row.append(value)
        table.add_row(*row)
    
    return table


async def list_iam_resources(
    match: str = None,
    resource_type: str = 'all'
) -> List[Dict[str, str]]:
    """List IAM resources (users and roles) with optional filters"""
    
    # IAM is global, so we only need to query one region
    regions = ['us-east-1']  # IAM is global but we need to specify a region for boto3
    
    users_response = {}
    roles_response = {}
    
    # Get users if requested
    if resource_type in ['all', 'users']:
        users_response = await aws_session.call_service_async(
            'iam', 
            'list_users',
            regions=regions
        )
    
    # Get roles if requested
    if resource_type in ['all', 'roles']:
        roles_response = await aws_session.call_service_async(
            'iam', 
            'list_roles',
            regions=regions
        )
    
    # Format the data
    resources = format_iam_data(users_response, roles_response, resource_type)
    
    # Apply match filter (fuzzy search on name, type, and path)
    if match:
        match_lower = match.lower()
        filtered_resources = []
        for resource in resources:
            # Check if match is in name, type, or path
            searchable_text = f"{resource['Name']} {resource['Type']} {resource['Path']}".lower()
            if match_lower in searchable_text:
                filtered_resources.append(resource)
        resources = filtered_resources
    
    return resources 