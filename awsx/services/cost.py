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
        elif abs(cost_float) < 0.01:
            return "<$0.01"
        else:
            return f"${cost_float:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def get_date_range(days: int = 30) -> tuple[str, str]:
    """Get date range for cost analysis"""
    # End date should be yesterday (Cost Explorer has 1-2 day delay)
    end_date = (datetime.now() - timedelta(days=1)).date()
    start_date = end_date - timedelta(days=days-1)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def get_current_month_range() -> tuple[str, str]:
    """Get current month date range"""
    now = datetime.now()
    start_of_month = now.replace(day=1).date()
    # End date should be yesterday for Cost Explorer
    end_date = (now - timedelta(days=1)).date()
    return start_of_month.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


async def get_current_month_costs(debug: bool = False) -> Dict[str, str]:
    """Get current month costs - this should match what you see in AWS console"""
    start_date, end_date = get_current_month_range()
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Querying current month costs from {start_date} to {end_date}[/dim]")
        
        # Try different combinations of metrics
        metrics_to_try = ['BlendedCost', 'UnblendedCost', 'NetBlendedCost', 'NetUnblendedCost']
        
        results = {}
        
        for metric in metrics_to_try:
            try:
                response = ce_client.get_cost_and_usage(
                    TimePeriod={
                        'Start': start_date,
                        'End': end_date
                    },
                    Granularity='DAILY',
                    Metrics=[metric]
                )
                
                total_cost = 0.0
                for result in response.get('ResultsByTime', []):
                    amount = float(result['Total'][metric]['Amount'])
                    total_cost += amount
                
                results[metric] = {
                    'amount': total_cost,
                    'formatted': format_cost_amount(str(total_cost))
                }
                
                if debug:
                    console.print(f"[cyan]{metric}: ${total_cost:.6f}[/cyan]")
                    
            except Exception as e:
                if debug:
                    console.print(f"[red]Error with {metric}: {e}[/red]")
                results[metric] = {'amount': 0.0, 'formatted': 'Error'}
        
        # Find the metric with the highest value (most likely to be correct)
        best_metric = max(results.items(), key=lambda x: abs(x[1]['amount']))
        
        console.print(f"[green]Best metric: {best_metric[0]} = {best_metric[1]['formatted']}[/green]")
        
        return {
            'period': f"Month-to-date ({start_date} to {end_date})",
            'total_cost': best_metric[1]['formatted'],
            'metric_used': best_metric[0],
            'all_metrics': {k: v['formatted'] for k, v in results.items()}
        }
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting current month costs: {e}[/red]")
        return {
            'period': "Month-to-date",
            'total_cost': "Error",
            'metric_used': "Unknown",
            'all_metrics': {}
        }


async def get_cost_by_service(days: int = 30, limit: int = 10, debug: bool = False) -> List[Dict[str, str]]:
    """Get cost breakdown by AWS service"""
    start_date, end_date = get_date_range(days)
    
    try:
        # Cost Explorer is only available in us-east-1
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Querying Cost Explorer from {start_date} to {end_date}[/dim]")
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',  # Changed from MONTHLY to DAILY
            Metrics=['UnblendedCost'],  # Changed from BlendedCost to UnblendedCost
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        if debug:
            console.print(f"[cyan]Raw API Response:[/cyan]")
            import json
            console.print(json.dumps(response, indent=2, default=str))
        
        # Aggregate costs by service across all days
        service_totals = {}
        for result in response.get('ResultsByTime', []):
            date = result.get('TimePeriod', {}).get('Start', 'Unknown')
            if debug:
                console.print(f"[dim]Processing date: {date}[/dim]")
            
            for group in result.get('Groups', []):
                service_name = group['Keys'][0] if group['Keys'] else 'Unknown'
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if debug and amount > 0:
                    console.print(f"[dim]  {service_name}: ${amount:.6f}[/dim]")
                
                if service_name in service_totals:
                    service_totals[service_name] += amount
                else:
                    service_totals[service_name] = amount
        
        # Convert to list format
        services_cost = []
        for service_name, total_amount in service_totals.items():
            if total_amount > 0:  # Only include services with actual cost
                services_cost.append({
                    'Service': service_name,
                    'Cost': format_cost_amount(str(total_amount)),
                    'Raw_Cost': total_amount
                })
        
        # Sort by cost and limit results
        services_cost.sort(key=lambda x: x['Raw_Cost'], reverse=True)
        
        # Debug output
        total_cost = sum(item['Raw_Cost'] for item in services_cost)
        console.print(f"[dim]Total cost found: ${total_cost:.6f} across {len(services_cost)} services[/dim]")
        
        return services_cost[:limit]
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting cost data: {e}[/red]")
        console.print("[yellow]Note: Cost Explorer requires specific permissions and may have 24-48h data delay[/yellow]")
        return []


async def get_cost_by_account(days: int = 30, debug: bool = False) -> List[Dict[str, str]]:
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
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'LINKED_ACCOUNT'
                }
            ]
        )
        
        if debug:
            console = Console()
            console.print(f"[cyan]Raw Account API Response:[/cyan]")
            import json
            console.print(json.dumps(response, indent=2, default=str))
        
        # Aggregate costs by account across all days
        account_totals = {}
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                account_id = group['Keys'][0] if group['Keys'] else 'Unknown'
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                
                if account_id in account_totals:
                    account_totals[account_id] += amount
                else:
                    account_totals[account_id] = amount
        
        # Convert to list format
        accounts_cost = []
        for account_id, total_amount in account_totals.items():
            if total_amount > 0:
                accounts_cost.append({
                    'Account': account_id,
                    'Cost': format_cost_amount(str(total_amount)),
                    'Raw_Cost': total_amount
                })
        
        accounts_cost.sort(key=lambda x: x['Raw_Cost'], reverse=True)
        return accounts_cost
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting account cost data: {e}[/red]")
        return []


async def get_daily_costs(days: int = 7, debug: bool = False) -> List[Dict[str, str]]:
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
            Metrics=['UnblendedCost']
        )
        
        if debug:
            console = Console()
            console.print(f"[cyan]Raw Daily API Response:[/cyan]")
            import json
            console.print(json.dumps(response, indent=2, default=str))
        
        daily_costs = []
        for result in response.get('ResultsByTime', []):
            date_str = result['TimePeriod']['Start']
            amount = result['Total']['UnblendedCost']['Amount']
            
            # Convert date to readable format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d')
            
            daily_costs.append({
                'Date': formatted_date,
                'Cost': format_cost_amount(amount),
                'Raw_Cost': float(amount)
            })
        
        return daily_costs
        
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


async def get_cost_summary(days: int = 30, debug: bool = False) -> Dict[str, str]:
    """Get overall cost summary"""
    start_date, end_date = get_date_range(days)
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        # Get current period cost
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        
        if debug:
            console = Console()
            console.print(f"[cyan]Raw Summary API Response:[/cyan]")
            import json
            console.print(json.dumps(response, indent=2, default=str))
        
        total_cost = 0.0
        for result in response.get('ResultsByTime', []):
            amount = float(result['Total']['UnblendedCost']['Amount'])
            total_cost += amount
        
        # Get previous period for comparison
        prev_end = datetime.strptime(start_date, '%Y-%m-%d').date()
        prev_start = prev_end - timedelta(days=days)
        
        prev_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': prev_start.strftime('%Y-%m-%d'),
                'End': prev_end.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )
        
        prev_total = 0.0
        for result in prev_response.get('ResultsByTime', []):
            amount = float(result['Total']['UnblendedCost']['Amount'])
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
        
        # Debug output
        console = Console()
        console.print(f"[dim]Period: {start_date} to {end_date}, Total: ${total_cost:.6f}, Previous: ${prev_total:.6f}[/dim]")
        
        return {
            'period': f"Last {days} days",
            'total_cost': format_cost_amount(str(total_cost)),
            'daily_avg': format_cost_amount(str(total_cost / days)) if days > 0 else "$0.00",
            'trend': trend
        }
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error in cost summary: {e}[/red]")
        return {
            'period': f"Last {days} days",
            'total_cost': "Error",
            'daily_avg': "Error", 
            'trend': "Error"
        }


async def get_specific_month_costs(year: int, month: int, debug: bool = False) -> Dict[str, str]:
    """Get costs for a specific month and year"""
    start_date = f"{year:04d}-{month:02d}-01"
    
    # Calculate end date (first day of next month)
    if month == 12:
        end_year = year + 1
        end_month = 1
    else:
        end_year = year
        end_month = month + 1
    end_date = f"{end_year:04d}-{end_month:02d}-01"
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Querying {year}-{month:02d} costs from {start_date} to {end_date}[/dim]")
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='MONTHLY',  # Use monthly for full month data
            Metrics=['BlendedCost']
        )
        
        if debug:
            console.print(f"[cyan]Raw API Response for {year}-{month:02d}:[/cyan]")
            import json
            console.print(json.dumps(response, indent=2, default=str))
        
        total_cost = 0.0
        for result in response.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            total_cost += amount
        
        return {
            'period': f"{year}-{month:02d}",
            'total_cost': format_cost_amount(str(total_cost)),
            'raw_amount': total_cost
        }
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting {year}-{month:02d} costs: {e}[/red]")
        return {
            'period': f"{year}-{month:02d}",
            'total_cost': "Error",
            'raw_amount': 0.0
        }


def check_low_cost_data(services_cost: List[Dict[str, str]], console: Console) -> bool:
    """Check if cost data seems unusually low and provide helpful guidance"""
    if not services_cost:
        return True
        
    total_cost = sum(item.get('Raw_Cost', 0) for item in services_cost)
    
    # If total costs are very low (less than $1), show guidance
    if total_cost < 1.0:
        console.print("\n[yellow]⚠️  Cost Explorer is showing very low amounts (likely credits/adjustments)[/yellow]")
        console.print("\n[bold]If your AWS console shows higher costs, this might be due to:[/bold]")
        console.print("  • Cost Explorer API showing net costs (after credits)")
        console.print("  • Different time zones between API and console")
        console.print("  • 24-48 hour data delay in Cost Explorer")
        console.print("  • Consolidated billing (if part of AWS Organization)")
        console.print("\n[cyan]💡 For accurate current costs, check your AWS Billing console directly[/cyan]")
        console.print("   https://console.aws.amazon.com/billing/home")
        return True
    
    return False 