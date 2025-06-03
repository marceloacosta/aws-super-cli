"""Lambda service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_lambda_data(functions_by_region: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format Lambda function data for display"""
    formatted_functions = []
    
    for region, response in functions_by_region.items():
        if not response or 'Functions' not in response:
            continue
            
        for func in response['Functions']:
            # Format last modified date
            last_modified = func.get('LastModified')
            if last_modified:
                # Lambda returns ISO format string, parse it
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                    last_modified_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    last_modified_str = last_modified
            else:
                last_modified_str = 'N/A'
            
            # Format memory and timeout
            memory_mb = func.get('MemorySize', 0)
            timeout_sec = func.get('Timeout', 0)
            
            # Format code size
            code_size = func.get('CodeSize', 0)
            if code_size > 1024 * 1024:
                code_size_str = f"{code_size / (1024*1024):.1f}MB"
            elif code_size > 1024:
                code_size_str = f"{code_size / 1024:.1f}KB"
            else:
                code_size_str = f"{code_size}B"
            
            # Get VPC info
            vpc_id = 'N/A'
            if func.get('VpcConfig') and func['VpcConfig'].get('VpcId'):
                vpc_id = func['VpcConfig']['VpcId']
            
            formatted_functions.append({
                'Function Name': func['FunctionName'],
                'Runtime': func.get('Runtime', 'N/A'),
                'State': func.get('State', 'N/A'),
                'Memory': f"{memory_mb}MB" if memory_mb else 'N/A',
                'Timeout': f"{timeout_sec}s" if timeout_sec else 'N/A',
                'Code Size': code_size_str,
                'Handler': func.get('Handler', 'N/A'),
                'VPC': vpc_id,
                'Region': region,
                'Last Modified': last_modified_str,
                'Description': func.get('Description', 'N/A')[:50] + ('...' if len(func.get('Description', '')) > 50 else '')
            })
    
    return formatted_functions


def create_lambda_table(functions: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for Lambda functions"""
    if not columns:
        columns = ['Function Name', 'Runtime', 'State', 'Memory', 'Timeout', 'Region']
    
    table = Table(title="Lambda Functions", show_header=True, header_style="bold magenta")
    
    # Add columns with appropriate styling
    for col in columns:
        if col == 'Function Name':
            table.add_column(col, style="cyan", min_width=20)
        elif col == 'State':
            table.add_column(col, style="green", min_width=10)
        elif col == 'Runtime':
            table.add_column(col, style="blue", min_width=12)
        elif col in ['Memory', 'Timeout']:
            table.add_column(col, style="yellow", min_width=8)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for func in functions:
        row = []
        for col in columns:
            value = func.get(col, 'N/A')
            # Color code states
            if col == 'State':
                if value == 'Active':
                    value = f"[green]{value}[/green]"
                elif value in ['Pending', 'Inactive']:
                    value = f"[yellow]{value}[/yellow]"
                elif value == 'Failed':
                    value = f"[red]{value}[/red]"
            row.append(value)
        table.add_row(*row)
    
    return table


async def list_lambda_functions(
    regions: List[str] = None,
    all_regions: bool = False,
    match: str = None,
    runtime: str = None
) -> List[Dict[str, str]]:
    """List Lambda functions across regions with optional filters"""
    
    # Determine regions to query
    if regions:
        # User specified specific regions - use those
        pass
    elif all_regions:
        # User wants all regions (default behavior)
        regions = aws_session.get_available_regions('lambda')
    else:
        # User wants current region only (--no-all-regions)
        try:
            import boto3
            session = boto3.Session()
            current_region = session.region_name or 'us-east-1'
            regions = [current_region]
        except:
            regions = ['us-east-1']
    
    # Make async calls - Lambda list_functions doesn't support complex filters
    kwargs = {}
    
    responses = await aws_session.call_service_async(
        'lambda', 
        'list_functions',
        regions=regions,
        **kwargs
    )
    
    # Format the data
    functions = format_lambda_data(responses)
    
    # Apply runtime filter
    if runtime:
        runtime_lower = runtime.lower()
        filtered_functions = []
        for func in functions:
            if runtime_lower in func['Runtime'].lower():
                filtered_functions.append(func)
        functions = filtered_functions
    
    # Apply match filter (fuzzy search on function name, runtime, and description)
    if match:
        match_lower = match.lower()
        filtered_functions = []
        for func in functions:
            # Check if match is in function name, runtime, or description
            searchable_text = f"{func['Function Name']} {func['Runtime']} {func['Description']}".lower()
            if match_lower in searchable_text:
                filtered_functions.append(func)
        functions = filtered_functions
    
    return functions 