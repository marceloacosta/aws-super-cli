"""Cost analysis operations using AWS Cost Explorer"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_cost_amount(amount: str) -> str:
    """Format cost amount for display"""
    try:
        cost_float = float(amount)
        if cost_float == 0:
            return "$0.00"
        elif cost_float < 0.01:
            return "<$0.01"
        else:
            return f"${cost_float:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def get_date_range(days: int = 30) -> tuple[str, str]:
    """Get date range for cost analysis"""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


async def get_cost_by_service(days: int = 30, limit: int = 10) -> List[Dict[str, str]]:
    """Get cost breakdown by AWS service"""
    start_date, end_date = get_date_range(days)
    
    try:
        # Cost Explorer is only available in us-east-1
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        services_cost = []
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service_name = group['Keys'][0] if group['Keys'] else 'Unknown'
                amount = group['Metrics']['BlendedCost']['Amount']
                
                if float(amount) > 0:  # Only include services with actual cost
                    services_cost.append({
                        'Service': service_name,
                        'Cost': format_cost_amount(amount),
                        'Raw_Cost': float(amount)
                    })
        
        # Sort by cost and limit results
        services_cost.sort(key=lambda x: x['Raw_Cost'], reverse=True)
        return services_cost[:limit]
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting cost data: {e}[/red]")
        console.print("[yellow]Note: Cost Explorer requires specific permissions and may not be available in all regions[/yellow]")
        return []


async def get_cost_by_account(days: int = 30) -> List[Dict[str, str]]:
    """Get cost breakdown by AWS account (for multi-account setups)"""
    start_date, end_date = get_date_range(days)
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'LINKED_ACCOUNT'
                }
            ]
        )
        
        accounts_cost = []
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                account_id = group['Keys'][0] if group['Keys'] else 'Unknown'
                amount = group['Metrics']['BlendedCost']['Amount']
                
                if float(amount) > 0:
                    accounts_cost.append({
                        'Account': account_id,
                        'Cost': format_cost_amount(amount),
                        'Raw_Cost': float(amount)
                    })
        
        accounts_cost.sort(key=lambda x: x['Raw_Cost'], reverse=True)
        return accounts_cost
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting account cost data: {e}[/red]")
        return []


async def get_daily_costs(days: int = 30) -> List[Dict[str, str]]:
    """Get daily cost trend"""
    start_date, end_date = get_date_range(days)
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost']
        )
        
        daily_costs = []
        for result in response.get('ResultsByTime', []):
            date_str = result['TimePeriod']['Start']
            amount = result['Total']['BlendedCost']['Amount']
            
            # Convert date to readable format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d')
            
            daily_costs.append({
                'Date': formatted_date,
                'Cost': format_cost_amount(amount),
                'Raw_Cost': float(amount)
            })
        
        return daily_costs[-7:]  # Return last 7 days
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting daily cost data: {e}[/red]")
        return []


def create_cost_table(cost_data: List[Dict[str, str]], title: str, columns: List[str] = None) -> Table:
    """Create a rich table for cost data"""
    if not columns:
        columns = list(cost_data[0].keys()) if cost_data else ['Service', 'Cost']
        # Remove raw cost column from display
        columns = [col for col in columns if not col.startswith('Raw_')]
    
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    for col in columns:
        if 'Cost' in col:
            table.add_column(col, style="green", min_width=12, justify="right")
        elif 'Service' in col:
            table.add_column(col, style="cyan", min_width=20)
        elif 'Account' in col:
            table.add_column(col, style="yellow", min_width=12)
        else:
            table.add_column(col, min_width=8)
    
    for item in cost_data:
        row = []
        for col in columns:
            value = item.get(col, 'N/A')
            row.append(str(value))
        table.add_row(*row)
    
    return table


async def get_cost_summary(days: int = 30) -> Dict[str, str]:
    """Get overall cost summary"""
    start_date, end_date = get_date_range(days)
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost']
        )
        
        total_cost = 0.0
        for result in response.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            total_cost += amount
        
        # Get previous period for comparison
        prev_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
        prev_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': prev_start,
                'End': start_date
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost']
        )
        
        prev_total = 0.0
        for result in prev_response.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            prev_total += amount
        
        # Calculate trend
        trend = "→"
        if prev_total > 0:
            change_pct = ((total_cost - prev_total) / prev_total) * 100
            if change_pct > 5:
                trend = f"↗ +{change_pct:.1f}%"
            elif change_pct < -5:
                trend = f"↘ {change_pct:.1f}%"
            else:
                trend = f"→ {change_pct:+.1f}%"
        
        return {
            'period': f"Last {days} days",
            'total_cost': format_cost_amount(str(total_cost)),
            'daily_avg': format_cost_amount(str(total_cost / days)),
            'trend': trend
        }
        
    except Exception as e:
        return {
            'period': f"Last {days} days",
            'total_cost': "Error",
            'daily_avg': "Error", 
            'trend': "Error"
        } 