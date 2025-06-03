"""Cost analysis operations using AWS Cost Explorer"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def get_credits_filter() -> Dict[str, Any]:
    """Get the filter to exclude credits and refunds, matching AWS Console behavior
    
    This is critical! The AWS Console excludes credits/refunds by default,
    but the Cost Explorer API includes them, causing major discrepancies.
    """
    return {
        "Not": {
            "Dimensions": {
                "Key": "RECORD_TYPE",
                "Values": ["Refund", "Credit"]
            }
        }
    }


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
    """Get date range for cost analysis
    
    Note: Cost Explorer API treats end dates as EXCLUSIVE
    So to get full months, end date should be first day of next period
    """
    # End date should be yesterday (Cost Explorer has 1-2 day delay)
    end_date = (datetime.now() - timedelta(days=1)).date()
    start_date = end_date - timedelta(days=days-1)
    
    # Make end_date exclusive by adding 1 day
    # This ensures we include the full period up to end_date
    end_date_exclusive = end_date + timedelta(days=1)
    
    return start_date.strftime('%Y-%m-%d'), end_date_exclusive.strftime('%Y-%m-%d')


def get_current_month_range() -> tuple[str, str]:
    """Get current month date range with proper exclusive end date"""
    now = datetime.now()
    start_of_month = now.replace(day=1).date()
    
    # End date should be yesterday for Cost Explorer (with data delay)
    end_date = (now - timedelta(days=1)).date()
    
    # Make end_date exclusive by adding 1 day
    end_date_exclusive = end_date + timedelta(days=1)
    
    return start_of_month.strftime('%Y-%m-%d'), end_date_exclusive.strftime('%Y-%m-%d')


async def get_current_month_costs(debug: bool = False) -> Dict[str, str]:
    """Get current month costs showing both gross and net amounts"""
    start_date, end_date = get_current_month_range()
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Querying current month costs from {start_date} to {end_date}[/dim]")
        
        # Get GROSS costs (without credits)
        response_gross = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            Filter=get_credits_filter()
        )
        
        # Get NET costs (with credits)
        response_net = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost']
        )
        
        if debug:
            console.print(f"[cyan]Raw API Responses:[/cyan]")
            import json
            console.print("Gross:", json.dumps(response_gross, indent=2, default=str))
            console.print("Net:", json.dumps(response_net, indent=2, default=str))
        
        # Calculate totals
        gross_total = 0.0
        for result in response_gross.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            gross_total += amount
        
        net_total = 0.0
        for result in response_net.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            net_total += amount
        
        credits_applied = gross_total - net_total
        
        console.print(f"[green]Current month: Gross ${gross_total:.2f}, Net ${net_total:.2f}, Credits ${credits_applied:.2f}[/green]")
        
        return {
            'period': f"Month-to-date ({start_date} to {end_date})",
            'gross_cost': format_cost_amount(str(gross_total)),
            'net_cost': format_cost_amount(str(net_total)),
            'credits_applied': format_cost_amount(str(credits_applied))
        }
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error getting current month costs: {e}[/red]")
        return {
            'period': "Month-to-date",
            'gross_cost': "Error",
            'net_cost': "Error",
            'credits_applied': "Error"
        }


async def get_cost_by_service(days: int = 30, limit: int = 10, debug: bool = False, include_credits: bool = False) -> List[Dict[str, str]]:
    """Get cost breakdown by AWS service with option to include/exclude credits"""
    start_date, end_date = get_date_range(days)
    
    try:
        # Cost Explorer is only available in us-east-1
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Querying Cost Explorer from {start_date} to {end_date}[/dim]")
        
        # Build filter conditionally
        query_filter = None if include_credits else get_credits_filter()
        cost_type = "with credits" if include_credits else "without credits"
        
        # Build the request parameters
        request_params = {
            'TimePeriod': {
                'Start': start_date,
                'End': end_date
            },
            'Granularity': 'DAILY',
            'Metrics': ['BlendedCost'],
            'GroupBy': [
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        }
        
        # Only add Filter if we have one
        if query_filter is not None:
            request_params['Filter'] = query_filter
        
        response = ce_client.get_cost_and_usage(**request_params)
        
        if debug:
            console.print(f"[cyan]Raw API Response ({cost_type}):[/cyan]")
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
                amount = float(group['Metrics']['BlendedCost']['Amount'])
                
                if debug and amount != 0:  # Show both positive and negative
                    console.print(f"[dim]  {service_name}: ${amount:.6f}[/dim]")
                
                if service_name in service_totals:
                    service_totals[service_name] += amount
                else:
                    service_totals[service_name] = amount
        
        # Convert to list format
        services_cost = []
        for service_name, total_amount in service_totals.items():
            if abs(total_amount) > 0.001:  # Include both positive and negative amounts
                services_cost.append({
                    'Service': service_name,
                    'Cost': format_cost_amount(str(total_amount)),
                    'Raw_Cost': total_amount
                })
        
        # Sort by absolute cost value (highest impact first)
        services_cost.sort(key=lambda x: abs(x['Raw_Cost']), reverse=True)
        
        # Debug output
        total_cost = sum(item['Raw_Cost'] for item in services_cost)
        console.print(f"[green]Total cost found ({cost_type}): ${total_cost:.2f} across {len(services_cost)} services[/green]")
        
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
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'LINKED_ACCOUNT'
                }
            ],
            Filter=get_credits_filter()  # EXCLUDE CREDITS!
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
                amount = float(group['Metrics']['BlendedCost']['Amount'])
                
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
            Metrics=['BlendedCost'],
            Filter=get_credits_filter()  # EXCLUDE CREDITS!
        )
        
        if debug:
            console = Console()
            console.print(f"[cyan]Raw Daily API Response:[/cyan]")
            import json
            console.print(json.dumps(response, indent=2, default=str))
        
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
    """Get overall cost summary with both gross and net costs"""
    start_date, end_date = get_date_range(days)
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        # Get GROSS costs (without credits) - matches console default
        response_gross = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            Filter=get_credits_filter()  # EXCLUDE CREDITS!
        )
        
        # Get NET costs (with credits applied) - actual spend
        response_net = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost']
            # No filter = includes credits
        )
        
        if debug:
            console = Console()
            console.print(f"[cyan]Raw Summary API Responses:[/cyan]")
            import json
            console.print("Gross (no credits):", json.dumps(response_gross, indent=2, default=str))
            console.print("Net (with credits):", json.dumps(response_net, indent=2, default=str))
        
        # Calculate gross total
        gross_total = 0.0
        for result in response_gross.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            gross_total += amount
        
        # Calculate net total
        net_total = 0.0
        for result in response_net.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            net_total += amount
        
        # Calculate credits applied
        credits_applied = gross_total - net_total
        
        # Get previous period for trend (using gross costs)
        prev_end = datetime.strptime(start_date, '%Y-%m-%d').date()
        prev_start = prev_end - timedelta(days=days)
        
        prev_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': prev_start.strftime('%Y-%m-%d'),
                'End': prev_end.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            Filter=get_credits_filter()  # Compare gross-to-gross
        )
        
        prev_total = 0.0
        for result in prev_response.get('ResultsByTime', []):
            amount = float(result['Total']['BlendedCost']['Amount'])
            prev_total += amount
        
        # Calculate trend
        trend = "→"
        if prev_total > 0:
            change_pct = ((gross_total - prev_total) / prev_total) * 100
            if change_pct > 5:
                trend = f"↗ +{change_pct:.1f}%"
            elif change_pct < -5:
                trend = f"↘ {change_pct:.1f}%"
            else:
                trend = f"→ {change_pct:+.1f}%"
        
        # Debug output
        console = Console()
        console.print(f"[green]Period: {start_date} to {end_date}[/green]")
        console.print(f"[green]Gross: ${gross_total:.2f}, Net: ${net_total:.2f}, Credits: ${credits_applied:.2f}[/green]")
        
        return {
            'period': f"Last {days} days",
            'gross_cost': format_cost_amount(str(gross_total)),
            'net_cost': format_cost_amount(str(net_total)),
            'credits_applied': format_cost_amount(str(credits_applied)),
            'daily_avg_gross': format_cost_amount(str(gross_total / days)) if days > 0 else "$0.00",
            'daily_avg_net': format_cost_amount(str(net_total / days)) if days > 0 else "$0.00",
            'trend': trend
        }
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error in cost summary: {e}[/red]")
        return {
            'period': f"Last {days} days",
            'gross_cost': "Error",
            'net_cost': "Error",
            'credits_applied': "Error",
            'daily_avg_gross': "Error", 
            'daily_avg_net': "Error",
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
            Metrics=['BlendedCost'],
            Filter=get_credits_filter()  # EXCLUDE CREDITS!
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
        console.print("\n[green]✅ Cost data properly excludes AWS credits[/green]")
        console.print("[cyan]📊 If you still see $0, your account may have minimal costs[/cyan]")
        return False
        
    total_cost = sum(item.get('Raw_Cost', 0) for item in services_cost)
    
    # Updated guidance now that we exclude credits
    if total_cost < 1.0:
        console.print("\n[cyan]💡 Tips for accurate cost data:[/cyan]")
        console.print("  • Cost Explorer has 24-48 hour data delay")
        console.print("  • Very recent usage may not appear yet")
        console.print("  • Free tier usage won't show costs")
        console.print("  • awsx excludes credits to match console behavior")
        
        return False  # No longer show as problematic
    
    return False 


async def get_credit_analysis(days: int = 90, debug: bool = False) -> Dict[str, Any]:
    """Get comprehensive credit usage analysis and trends"""
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Analyzing credit usage patterns over last {days} days...[/dim]")
        
        # Get monthly credit usage for trend analysis
        monthly_data = []
        
        # Get last 3 months of data for trend analysis
        from datetime import datetime, timedelta
        import calendar
        
        end_date = datetime.now().date()
        
        for i in range(3):  # Last 3 months
            if i == 0:
                # Current month (partial)
                month_start = end_date.replace(day=1)
                month_end = end_date + timedelta(days=1)
            else:
                # Previous months (complete)
                temp_date = end_date.replace(day=1) - timedelta(days=i*30)
                month_start = temp_date.replace(day=1)
                
                # Get last day of the month
                last_day = calendar.monthrange(temp_date.year, temp_date.month)[1]
                month_end = temp_date.replace(day=last_day) + timedelta(days=1)
            
            # Get gross costs (without credits)
            response_gross = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': month_start.strftime('%Y-%m-%d'),
                    'End': month_end.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                Filter=get_credits_filter()
            )
            
            # Get net costs (with credits)
            response_net = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': month_start.strftime('%Y-%m-%d'),
                    'End': month_end.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost']
            )
            
            gross_total = 0.0
            for result in response_gross.get('ResultsByTime', []):
                gross_total += float(result['Total']['BlendedCost']['Amount'])
            
            net_total = 0.0
            for result in response_net.get('ResultsByTime', []):
                net_total += float(result['Total']['BlendedCost']['Amount'])
            
            credits_used = gross_total - net_total
            
            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'gross_cost': gross_total,
                'net_cost': net_total,
                'credits_used': credits_used,
                'is_current': i == 0
            })
        
        # Analyze credit usage trends
        credit_usage_trend = []
        total_credits_used = 0
        
        for month_data in reversed(monthly_data):  # Oldest to newest
            credit_usage_trend.append({
                'month': month_data['month'],
                'credits_used': month_data['credits_used'],
                'gross_cost': month_data['gross_cost']
            })
            total_credits_used += month_data['credits_used']
        
        # Calculate average monthly credit usage (excluding current partial month)
        complete_months = [m for m in monthly_data if not m['is_current']]
        avg_monthly_credits = sum(m['credits_used'] for m in complete_months) / len(complete_months) if complete_months else 0
        
        # Get current month credit usage rate
        current_month = monthly_data[0]  # First item is current month
        days_in_month = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
        current_day = datetime.now().day
        
        # Project current month usage
        if current_day > 0:
            daily_credit_rate = current_month['credits_used'] / current_day
            projected_month_credits = daily_credit_rate * days_in_month
        else:
            projected_month_credits = 0
        
        # Estimate credit runway (Note: We can't get actual remaining balance from API)
        runway_estimate = "Unknown - AWS API doesn't provide remaining credit balance"
        if avg_monthly_credits > 10:  # Only estimate if significant usage
            # This is a rough estimate - users need to check console for actual balance
            runway_estimate = f"~{avg_monthly_credits:.0f} credits/month usage rate - Check AWS Console for actual balance"
        
        if debug:
            console.print(f"[cyan]Credit Analysis Debug:[/cyan]")
            for month in credit_usage_trend:
                console.print(f"  {month['month']}: ${month['credits_used']:.2f} credits")
        
        return {
            'total_credits_analyzed': total_credits_used,
            'avg_monthly_usage': avg_monthly_credits,
            'current_month_usage': current_month['credits_used'],
            'projected_month_usage': projected_month_credits,
            'credit_usage_trend': credit_usage_trend,
            'runway_estimate': runway_estimate,
            'analysis_period': f"Last 3 months",
            'note': "AWS API doesn't provide remaining credit balance - check AWS Console for actual balance"
        }
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error analyzing credits: {e}[/red]")
        return {
            'error': str(e),
            'note': "Credit analysis requires Cost Explorer permissions"
        }


async def get_credit_usage_by_service(days: int = 30, debug: bool = False) -> List[Dict[str, Any]]:
    """Get credit usage breakdown by service to see which services consume most credits"""
    start_date, end_date = get_date_range(days)
    
    try:
        session = aws_session.session
        ce_client = session.client('ce', region_name='us-east-1')
        
        console = Console()
        console.print(f"[dim]Analyzing credit impact by service from {start_date} to {end_date}...[/dim]")
        
        # Get gross costs by service (without credits)
        response_gross = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[{
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }],
            Filter=get_credits_filter()
        )
        
        # Get net costs by service (with credits)
        response_net = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[{
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }]
        )
        
        # Aggregate gross costs by service
        gross_by_service = {}
        for result in response_gross.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0] if group['Keys'] else 'Unknown'
                amount = float(group['Metrics']['BlendedCost']['Amount'])
                
                if service in gross_by_service:
                    gross_by_service[service] += amount
                else:
                    gross_by_service[service] = amount
        
        # Aggregate net costs by service
        net_by_service = {}
        for result in response_net.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service = group['Keys'][0] if group['Keys'] else 'Unknown'
                amount = float(group['Metrics']['BlendedCost']['Amount'])
                
                if service in net_by_service:
                    net_by_service[service] += amount
                else:
                    net_by_service[service] = amount
        
        # Calculate credit impact by service
        credit_impact = []
        for service in gross_by_service:
            gross_cost = gross_by_service[service]
            net_cost = net_by_service.get(service, 0)
            credits_applied = gross_cost - net_cost
            
            if credits_applied > 0.01:  # Only include services with meaningful credit usage
                credit_impact.append({
                    'Service': service,
                    'Gross_Cost': format_cost_amount(str(gross_cost)),
                    'Net_Cost': format_cost_amount(str(net_cost)),
                    'Credits_Applied': format_cost_amount(str(credits_applied)),
                    'Credit_Coverage': f"{(credits_applied/gross_cost*100):.1f}%" if gross_cost > 0 else "0%",
                    'Raw_Credits': credits_applied
                })
        
        # Sort by credit usage
        credit_impact.sort(key=lambda x: x['Raw_Credits'], reverse=True)
        
        if debug:
            console.print(f"[cyan]Services with credit coverage:[/cyan]")
            for item in credit_impact[:5]:
                console.print(f"  {item['Service']}: {item['Credits_Applied']} ({item['Credit_Coverage']} coverage)")
        
        return credit_impact
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error analyzing credit usage by service: {e}[/red]")
        return []


def create_credit_analysis_table(credit_data: Dict[str, Any]) -> Table:
    """Create a rich table for credit analysis"""
    table = Table(title="💳 AWS Credits Analysis", show_header=True, header_style="bold magenta")
    
    table.add_column("Metric", style="cyan", min_width=25)
    table.add_column("Value", style="green", min_width=20)
    table.add_column("Notes", style="dim", min_width=30)
    
    table.add_row(
        "Analysis Period",
        credit_data.get('analysis_period', 'N/A'),
        "Historical credit usage data"
    )
    
    table.add_row(
        "Total Credits (3 months)",
        format_cost_amount(str(credit_data.get('total_credits_analyzed', 0))),
        "Credits consumed in analysis period"
    )
    
    table.add_row(
        "Average Monthly Usage",
        format_cost_amount(str(credit_data.get('avg_monthly_usage', 0))),
        "Based on complete months only"
    )
    
    table.add_row(
        "Current Month Usage",
        format_cost_amount(str(credit_data.get('current_month_usage', 0))),
        "Month-to-date credit consumption"
    )
    
    table.add_row(
        "Projected Month Total",
        format_cost_amount(str(credit_data.get('projected_month_usage', 0))),
        "Estimated total for current month"
    )
    
    table.add_row(
        "Credit Runway",
        "Check AWS Console",
        credit_data.get('runway_estimate', 'AWS API limitation')
    )
    
    return table


def create_credit_usage_table(credit_usage: List[Dict[str, Any]], title: str = "Credit Usage by Service") -> Table:
    """Create a rich table for credit usage by service"""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    table.add_column("Service", style="cyan", min_width=25)
    table.add_column("Gross Cost", style="yellow", min_width=12, justify="right")
    table.add_column("Credits Applied", style="green", min_width=15, justify="right")
    table.add_column("Net Cost", style="blue", min_width=12, justify="right")
    table.add_column("Coverage", style="magenta", min_width=10, justify="center")
    
    for item in credit_usage:
        table.add_row(
            item['Service'],
            item['Gross_Cost'],
            item['Credits_Applied'],
            item['Net_Cost'],
            item['Credit_Coverage']
        )
    
    return table 