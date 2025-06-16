"""AWS Super CLI - Main CLI interface"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
import typer
from rich.console import Console
from rich import print as rprint
from rich.table import Table

from .services import ec2, s3, vpc, rds, elb, iam
from .services import lambda_
from .services import cost as cost_analysis
from .services import audit as audit_service
from .aws import aws_session
from .utils.arn_intelligence import arn_intelligence
from .utils.account_intelligence import account_intelligence, AccountCategory

app = typer.Typer(
    name="aws-super-cli",
    help="AWS Super CLI – Your AWS resource discovery and security tool",
    epilog="Need help? Run 'aws-super-cli help' for detailed examples and usage patterns.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Handle the case when no command is provided"""
    if ctx.invoked_subcommand is None:
        # Show clean help when no arguments provided
        help_command()
        raise typer.Exit()

def should_use_clean_output() -> bool:
    """Check if we should use clean output without Rich markup.
    
    This is important for tests and environments where Rich markup should not leak.
    """
    import sys
    import os
    
    # Check for common test runners and non-interactive environments
    if (hasattr(sys, '_called_from_test') or 
        'pytest' in sys.modules or 
        'unittest' in sys.modules or
        'TEST_MODE' in os.environ or
        not sys.stdout.isatty()):
        return True
    
    return False

def safe_print(text: str = "", fallback_text: str = None):
    """Print text with Rich markup if in interactive mode, plain text otherwise.
    
    Args:
        text: Text with Rich markup for interactive display
        fallback_text: Plain text version (if None, strips markup from text)
    """
    import sys
    
    if should_use_clean_output():
        # Handle Rich Table objects
        if hasattr(text, '__class__') and 'Table' in str(text.__class__):
            # For tables in test environments, we need to use console.print
            # but with a plain console that doesn't add markup
            from rich.console import Console
            plain_console = Console(file=sys.stdout, force_terminal=False, no_color=True)
            plain_console.print(text)
            return
            
        if fallback_text:
            print(fallback_text)
        elif text == "":
            print()  # Handle empty string case
        else:
            # Strip Rich markup tags for clean output
            import re
            clean_text = re.sub(r'\[/?[^\]]*\]', '', text)
            print(clean_text)
    else:
        if text == "":
            rprint()  # Handle empty string case
        else:
            rprint(text)

@app.command(name="ls", help="List AWS resources across regions with beautiful output")
def list_resources(
    service: Optional[str] = typer.Argument(None, help="Service to list (ec2, s3, vpc, rds, lambda, elb, iam)"),
    region: Optional[str] = typer.Option(None, "-r", "--region", help="Specific region to query"),
    all_regions: bool = typer.Option(True, "--all-regions/--no-all-regions", help="Query all regions (default) or current region only"),
    all_accounts: bool = typer.Option(False, "--all-accounts", help="Query all accessible AWS accounts"),
    accounts: Optional[str] = typer.Option(None, "--accounts", help="Comma-separated profiles or pattern (e.g., 'prod-*,staging')"),
    match: Optional[str] = typer.Option(None, "-m", "--match", help="Filter resources by name/tags (fuzzy match)"),
    columns: Optional[str] = typer.Option(None, "-c", "--columns", help="Comma-separated list of columns to display"),
    show_full_arns: bool = typer.Option(False, "--show-full-arns", help="Show full ARNs instead of smart truncated versions"),
    # EC2 specific filters
    state: Optional[str] = typer.Option(None, "--state", help="Filter EC2 instances by state (running, stopped, etc.)"),
    instance_type: Optional[str] = typer.Option(None, "--instance-type", help="Filter EC2 instances by instance type"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter resources by tag (format: key=value)"),
    # RDS specific filters
    engine: Optional[str] = typer.Option(None, "--engine", help="Filter RDS instances by engine (mysql, postgres, etc.)"),
    # Lambda specific filters
    runtime: Optional[str] = typer.Option(None, "--runtime", help="Filter Lambda functions by runtime (python, node, etc.)"),
    # ELB specific filters
    type_filter: Optional[str] = typer.Option(None, "--type", help="Filter load balancers by type (classic, application, network)"),
    # IAM specific filters
    iam_type: Optional[str] = typer.Option(None, "--iam-type", help="Filter IAM resources by type (users, roles, all)"),
):
    """List AWS resources with beautiful output"""
    
    # Handle missing service argument gracefully
    if service is None:
        safe_print("Which AWS service would you like to list?")
        safe_print()
        safe_print("Available services:")
        safe_print("  aws-super-cli ls ec2                    # List EC2 instances")
        safe_print("  aws-super-cli ls s3                     # List S3 buckets")
        safe_print("  aws-super-cli ls vpc                    # List VPCs")
        safe_print("  aws-super-cli ls rds                    # List RDS databases")
        safe_print("  aws-super-cli ls lambda                 # List Lambda functions")
        safe_print("  aws-super-cli ls elb                    # List load balancers")
        safe_print("  aws-super-cli ls iam                    # List IAM resources")
        safe_print()
        safe_print("Quick examples:")
        safe_print("  aws-super-cli ls ec2 --all-accounts       # EC2 across all accounts")
        safe_print("  aws-super-cli ls rds --engine postgres    # Find PostgreSQL databases")
        safe_print("  aws-super-cli help                       # Show more examples")
        return
    
    # Define supported services and aliases
    SUPPORTED_SERVICES = ['ec2', 's3', 'vpc', 'rds', 'lambda', 'elb', 'iam']
    SERVICE_ALIASES = {
        'instances': 'ec2',
        'instance': 'ec2',
        'servers': 'ec2',
        'vms': 'ec2',
        'buckets': 's3',
        'bucket': 's3',
        'storage': 's3',
        'databases': 'rds',
        'database': 'rds',
        'db': 'rds',
        'functions': 'lambda',
        'function': 'lambda',
        'lambdas': 'lambda',
        'loadbalancers': 'elb',
        'loadbalancer': 'elb',
        'load-balancers': 'elb',
        'load-balancer': 'elb',
        'lb': 'elb',
        'alb': 'elb',
        'nlb': 'elb',
        'users': 'iam',
        'roles': 'iam',
        'policies': 'iam',
        'identity': 'iam'
    }
    
    # Normalize service name
    service_lower = service.lower()
    
    # Check if it's an alias first
    if service_lower in SERVICE_ALIASES:
        service = SERVICE_ALIASES[service_lower]
        safe_print(f"Interpreting '{service_lower}' as '{service}'")
    
    # Check if service is supported
    if service not in SUPPORTED_SERVICES:
        # Find fuzzy matches and deduplicate
        from difflib import get_close_matches
        suggestions = get_close_matches(service_lower, SUPPORTED_SERVICES + list(SERVICE_ALIASES.keys()), n=5, cutoff=0.3)
        
        # Deduplicate suggestions by converting aliases to actual services
        unique_suggestions = []
        seen_services = set()
        for suggestion in suggestions:
            actual_service = SERVICE_ALIASES.get(suggestion, suggestion)
            if actual_service not in seen_services:
                unique_suggestions.append(actual_service)
                seen_services.add(actual_service)
        
        safe_print(f"Unknown service: '{service}'")
        safe_print()
        
        if unique_suggestions:
            safe_print("Did you mean:")
            for suggestion in unique_suggestions[:3]:  # Show max 3 suggestions
                safe_print(f"  aws-super-cli ls {suggestion}")
            safe_print()
        
        safe_print("Supported services:")
        for svc in SUPPORTED_SERVICES:
            safe_print(f"  aws-super-cli ls {svc}")
        
        safe_print()
        safe_print("Quick examples:")
        safe_print("  aws-super-cli ls ec2                    # List EC2 instances")
        safe_print("  aws-super-cli ls s3                     # List S3 buckets")  
        safe_print("  aws-super-cli ls rds --engine postgres    # Find PostgreSQL databases")
        safe_print("  aws-super-cli help                       # Show more examples")
        return
    
    # Multi-account support check
    multi_account_services = ['ec2']  # Services that support multi-account
    
    if all_accounts and service not in multi_account_services:
        safe_print(f"Multi-account support for {service} coming soon!")
        safe_print(f"Running single-account query for {service}...")
        safe_print()
        all_accounts = False
    elif accounts and service not in multi_account_services:
        safe_print(f"Multi-account support for {service} coming soon!")
        safe_print(f"Running single-account query for {service}...")
        safe_print()
        accounts = None
    
    # Rest of the existing function logic...
    try:
        if service == "ec2":
            if all_accounts or accounts:
                asyncio.run(ec2.list_ec2_instances_multi_account(
                    all_accounts=all_accounts, 
                    account_patterns=accounts.split(',') if accounts else None,
                    regions=region.split(',') if region else None,
                    all_regions=all_regions,
                    match=match,
                    state=state,
                    instance_type=instance_type,
                    tag=tag,
                    columns=columns.split(',') if columns else None
                ))
            else:
                asyncio.run(ec2.list_ec2_instances(
                    regions=region.split(',') if region else None,
                    all_regions=all_regions,
                    match=match,
                    state=state,
                    instance_type=instance_type,
                    tag=tag,
                    columns=columns.split(',') if columns else None
                ))
        elif service == "s3":
            asyncio.run(s3.list_s3_buckets(match=match))
        elif service == "vpc":
            asyncio.run(vpc.list_vpcs(
                regions=region.split(',') if region else None,
                all_regions=all_regions,
                match=match
            ))
        elif service == "rds":
            asyncio.run(rds.list_rds_instances(
                regions=region.split(',') if region else None,
                all_regions=all_regions,
                engine=engine,
                match=match
            ))
        elif service == "lambda":
            asyncio.run(lambda_.list_lambda_functions(
                regions=region.split(',') if region else None,
                all_regions=all_regions,
                runtime=runtime,
                match=match
            ))
        elif service == "elb":
            asyncio.run(elb.list_load_balancers(
                regions=region.split(',') if region else None,
                all_regions=all_regions,
                type_filter=type_filter,
                match=match
            ))
        elif service == "iam":
            # IAM service call with proper parameters
            async def run_iam_listing():
                resources = await iam.list_iam_resources(
                    match=match,
                    resource_type=iam_type or 'all',
                    show_full_arns=show_full_arns
                )
                if resources:
                    table = iam.create_iam_table(
                        resources, 
                        columns=columns.split(',') if columns else None,
                        show_full_arns=show_full_arns
                    )
                    safe_print(table)
                else:
                    safe_print("[yellow]No IAM resources found matching your criteria[/yellow]")
            
            asyncio.run(run_iam_listing())
        else:
            # This shouldn't happen now due to validation above, but keep as fallback
            safe_print(f"Multi-account support for {service} coming soon!")
            safe_print(f"Multi-account support currently available for: {', '.join(multi_account_services)}")
            safe_print(f"Single-account support available for: {', '.join([s for s in SUPPORTED_SERVICES if s not in multi_account_services])}")
            safe_print()
            safe_print("Examples:")
            safe_print("  aws-super-cli ls ec2 --all-accounts        # Multi-account EC2 (works now!)")
            safe_print("  aws-super-cli ls s3                        # Single-account S3")
            safe_print("  aws-super-cli ls rds --engine postgres     # Single-account RDS")
            safe_print("  aws-super-cli accounts                     # List available profiles")
    
    except Exception as e:
        with console.status("[bold red]Error occurred...", spinner="dots"):
            pass
        
        safe_print(f"❌ Error: {e}")
        
        # Provide helpful suggestions based on the error
        error_str = str(e).lower()
        if "credentials" in error_str or "access denied" in error_str:
            safe_print()
            safe_print("Credential issues detected. Try:")
            safe_print("  aws-super-cli version           # Check credential status")
            safe_print("  aws configure                  # Configure credentials")
            safe_print("  aws sts get-caller-identity    # Test AWS access")
        elif "region" in error_str:
            safe_print()
            safe_print("Region issues detected. Try:")
            safe_print(f"  aws-super-cli ls {service} --region us-east-1")
            safe_print("  aws configure set region us-east-1")
        
        # Always show debug info for now since we're in development
        safe_print()
        safe_print("[bold red]Debug info:[/bold red]")
        import traceback
        safe_print(f"[dim]{traceback.format_exc()}[/dim]")


@app.command()
def cost(
    command: Optional[str] = typer.Argument(None, help="Cost command (top-spend, with-credits, by-account, daily, summary, month, credits, credits-by-service)"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze (default: 30)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results to show (default: 10)"),
    debug: bool = typer.Option(False, "--debug", help="Show debug information including raw API responses"),
):
    """Analyze AWS costs and spending patterns"""
    
    # If no command provided, show summary by default
    if command is None:
        safe_print("Which cost analysis would you like?")
        safe_print()
        safe_print("Most Popular:")
        safe_print("  aws-super-cli cost summary              # Overall cost overview")
        safe_print("  aws-super-cli cost top-spend            # Biggest spending services")
        safe_print("  aws-super-cli cost credits              # Credit usage analysis")
        safe_print()
        safe_print("All Available Commands:")
        safe_print("  summary              # Comprehensive cost summary")
        safe_print("  top-spend            # Top spending services (gross costs)")
        safe_print("  with-credits         # Top spending services (net costs)")
        safe_print("  by-account           # Costs broken down by account")
        safe_print("  daily                # Daily cost trends")
        safe_print("  month                # Current month costs")
        safe_print("  credits              # Credit usage trends")
        safe_print("  credits-by-service   # Credit usage by service")
        safe_print()
        safe_print("Quick start:")
        safe_print("  aws-super-cli cost summary              # Start here!")
        return
    
    command_lower = command.lower()
    
    try:
        if command_lower == "top-spend":
            safe_print(f"Analyzing top spending services for the last {days} days...")
            
            # Pass debug flag
            services_cost = asyncio.run(cost_analysis.get_cost_by_service(days=days, limit=limit, debug=debug))
            if not services_cost:
                safe_print("[yellow]No cost data available. Check permissions and try again.[/yellow]")
                return
            
            # Check for low cost data and show guidance
            is_low_cost = cost_analysis.check_low_cost_data(services_cost, console)
            
            table = cost_analysis.create_cost_table(
                services_cost, 
                f"Top {len(services_cost)} AWS Services by Cost (Last {days} days) - Gross Costs"
            )
            safe_print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in services_cost)
            safe_print(f"\n[green]Total gross cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
            # Also show with credits applied for comparison
            safe_print(f"\n[dim]Use '--include-credits' flag to see costs with credits applied[/dim]")
            
        elif command_lower == "with-credits":
            safe_print(f"Analyzing top spending services (WITH credits applied) for the last {days} days...")
            
            services_cost = asyncio.run(cost_analysis.get_cost_by_service(days=days, limit=limit, debug=debug, include_credits=True))
            if not services_cost:
                safe_print("[yellow]No cost data available. Check permissions and try again.[/yellow]")
                return
            
            table = cost_analysis.create_cost_table(
                services_cost, 
                f"Top {len(services_cost)} AWS Services by Cost (Last {days} days) - Net Costs (With Credits)"
            )
            safe_print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in services_cost)
            safe_print(f"\n[green]Total net cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
        elif command_lower == "by-account":
            safe_print(f"Analyzing costs by account for the last {days} days...")
            
            accounts_cost = asyncio.run(cost_analysis.get_cost_by_account(days=days, debug=debug))
            if not accounts_cost:
                safe_print("[yellow]No account cost data available.[/yellow]")
                return
            
            # Check for low cost data
            cost_analysis.check_low_cost_data(accounts_cost, console)
            
            table = cost_analysis.create_cost_table(
                accounts_cost[:limit], 
                f"AWS Costs by Account (Last {days} days) - Gross Costs"
            )
            safe_print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in accounts_cost[:limit])
            safe_print(f"\n[green]Total gross cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
        elif command_lower == "daily":
            safe_print("Analyzing daily cost trends...")
            
            daily_costs = asyncio.run(cost_analysis.get_daily_costs(days=days, debug=debug))
            if not daily_costs:
                safe_print("[yellow]No daily cost data available.[/yellow]")
                return
            
            # Check for low cost data
            cost_analysis.check_low_cost_data(daily_costs, console)
            
            table = cost_analysis.create_cost_table(
                daily_costs, 
                "Daily Cost Trend (Last 7 days) - Gross Costs"
            )
            safe_print(table)
            
            if len(daily_costs) >= 2:
                yesterday_cost = daily_costs[-1]['Raw_Cost']
                day_before_cost = daily_costs[-2]['Raw_Cost']
                change = yesterday_cost - day_before_cost
                if change > 0:
                    safe_print(f"[yellow]Daily cost increased by {cost_analysis.format_cost_amount(str(change))}[/yellow]")
                elif change < 0:
                    safe_print(f"[green]Daily cost decreased by {cost_analysis.format_cost_amount(str(abs(change)))}[/green]")
                else:
                    safe_print("[blue]Daily cost remained stable[/blue]")
                    
        elif command_lower == "summary":
            safe_print(f"Getting cost summary for the last {days} days...")
            
            summary = asyncio.run(cost_analysis.get_cost_summary(days=days, debug=debug))
            
            safe_print("\n[bold]Cost Summary[/bold]")
            safe_print(f"Period: {summary['period']}")
            safe_print(f"Gross Cost (without credits): [green]{summary['gross_cost']}[/green]")
            safe_print(f"Net Cost (with credits):      [blue]{summary['net_cost']}[/blue]")
            safe_print(f"Credits Applied:              [yellow]{summary['credits_applied']}[/yellow]")
            safe_print(f"Daily Average (gross):        [cyan]{summary['daily_avg_gross']}[/cyan]")
            safe_print(f"Daily Average (net):          [dim]{summary['daily_avg_net']}[/dim]")
            safe_print(f"Trend: {summary['trend']}")
            
        elif command_lower == "month":
            safe_print("Getting current month costs (matches AWS console)...")
            
            month_data = asyncio.run(cost_analysis.get_current_month_costs(debug=debug))
            
            safe_print("\n[bold]Current Month Costs[/bold]")
            safe_print(f"Period: {month_data['period']}")
            safe_print(f"Gross Cost (without credits): [green]{month_data['gross_cost']}[/green]")
            safe_print(f"Net Cost (with credits):      [blue]{month_data['net_cost']}[/blue]")
            safe_print(f"Credits Applied:              [yellow]{month_data['credits_applied']}[/yellow]")
            
        elif command_lower == "credits":
            safe_print("Analyzing AWS credits usage patterns...")
            
            credit_analysis = asyncio.run(cost_analysis.get_credit_analysis(days=90, debug=debug))
            
            if 'error' in credit_analysis:
                safe_print(f"[red]Error: {credit_analysis['error']}[/red]")
                safe_print(f"[yellow]{credit_analysis['note']}[/yellow]")
                return
            
            # Show credit analysis table
            table = cost_analysis.create_credit_analysis_table(credit_analysis)
            safe_print(table)
            
            # Show monthly trend
            safe_print("\n[bold]Monthly Credit Usage Trend[/bold]")
            for month_data in credit_analysis['credit_usage_trend']:
                credits = cost_analysis.format_cost_amount(str(month_data['credits_used']))
                gross = cost_analysis.format_cost_amount(str(month_data['gross_cost']))
                safe_print(f"  {month_data['month']}: [yellow]{credits}[/yellow] credits applied (gross: [dim]{gross}[/dim])")
            
            # Important note about remaining balance
            safe_print(f"\n[bold yellow]Important:[/bold yellow]")
            safe_print(f"[dim]{credit_analysis['note']}[/dim]")
            safe_print(f"[cyan]To see remaining credit balance, visit:[/cyan]")
            safe_print(f"   [link]https://console.aws.amazon.com/billing/home#/credits[/link]")
            
        elif command_lower == "credits-by-service":
            safe_print(f"Analyzing credit usage by service (last {days} days)...")
            
            credit_usage = asyncio.run(cost_analysis.get_credit_usage_by_service(days=days, debug=debug))
            
            if not credit_usage:
                safe_print("[yellow]No services found with significant credit usage.[/yellow]")
                return
            
            # Show credit usage by service
            table = cost_analysis.create_credit_usage_table(
                credit_usage[:limit], 
                f"Top {min(len(credit_usage), limit)} Services by Credit Usage (Last {days} days)"
            )
            safe_print(table)
            
            # Summary
            total_credits_used = sum(item['Raw_Credits'] for item in credit_usage)
            safe_print(f"\n[green]Total credits applied across {len(credit_usage)} services: {cost_analysis.format_cost_amount(str(total_credits_used))}[/green]")
            
            # Show highest coverage services
            high_coverage = [s for s in credit_usage if float(s['Credit_Coverage'].replace('%', '')) > 90]
            if high_coverage:
                safe_print(f"\n[cyan]Services with >90% credit coverage:[/cyan]")
                for service in high_coverage[:3]:
                    safe_print(f"  • {service['Service']}: {service['Credit_Coverage']} coverage")
            
        else:
            safe_print(f"[red]Unknown cost command: {command}[/red]")
            safe_print("\n[bold]Available commands:[/bold]")
            safe_print("  aws-super-cli cost top-spend          # Show top spending services (gross costs)")
            safe_print("  aws-super-cli cost with-credits       # Show top spending services (net costs)")
            safe_print("  aws-super-cli cost by-account         # Show costs by account")
            safe_print("  aws-super-cli cost daily              # Show daily cost trends")
            safe_print("  aws-super-cli cost summary            # Show comprehensive cost summary")
            safe_print("  aws-super-cli cost month              # Show current month costs")
            safe_print("  aws-super-cli cost credits            # Show credit usage analysis and trends")
            safe_print("  aws-super-cli cost credits-by-service # Show credit usage breakdown by service")
            safe_print("\n[bold]Cost Types:[/bold]")
            safe_print("  • [green]Gross costs[/green]: What you'd pay without credits (matches console)")
            safe_print("  • [blue]Net costs[/blue]: What you actually pay after credits")
            safe_print("  • [yellow]Credits[/yellow]: Amount of credits applied")
            safe_print("\n[bold]Credit Analysis:[/bold]")
            safe_print("  • [cyan]Usage trends[/cyan]: Historical credit consumption patterns")
            safe_print("  • [magenta]Service breakdown[/magenta]: Which services use most credits")
            safe_print("  • [yellow]Coverage analysis[/yellow]: Credit coverage percentage by service")
            safe_print("\n[bold]Options:[/bold]")
            safe_print("  --days 7                 # Analyze last 7 days")
            safe_print("  --limit 5                # Show top 5 results")
            safe_print("  --debug                  # Show debug information")
            
    except Exception as e:
        safe_print(f"[red]Error analyzing costs: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            safe_print("")
            for message in help_messages:
                safe_print(message)
        safe_print("\n[yellow]Note: Cost analysis requires Cost Explorer permissions:")
        safe_print("  • ce:GetCostAndUsage")
        safe_print("  • ce:GetDimensionValues")
        raise typer.Exit(1)


@app.command()
def version():
    """Show AWS Super CLI version and current AWS context"""
    from . import __version__
    
    safe_print(f"[bold cyan]AWS Super CLI[/bold cyan] version {__version__}")
    
    # Show AWS context
    try:
        has_creds, account_id, error = aws_session.check_credentials()
        
        if has_creds and account_id:
            # Working credentials
            credential_source = aws_session.detect_credential_source()
            
            # Test region detection  
            import boto3
            session = boto3.Session()
            region = session.region_name or 'us-east-1'
            
            safe_print(f"Credentials working: {credential_source}")
            safe_print(f"Account ID: {account_id}")
            safe_print(f"Default region: {region}")
            
            # Test basic AWS access
            try:
                session = aws_session.session
                ec2 = session.client('ec2', region_name=region or 'us-east-1')
                
                # Quick test - list instances (this is free)
                response = ec2.describe_instances(MaxResults=5)
                instance_count = sum(len(reservation['Instances']) for reservation in response['Reservations'])
                
                if instance_count > 0:
                    safe_print(f"EC2 API access working - found {instance_count} instances in {region or 'us-east-1'}")
                else:
                    safe_print(f"EC2 API access working - no instances in {region or 'us-east-1'}")
                    
            except Exception as e:
                safe_print(f"EC2 API error: {e}")
                help_messages = aws_session.get_credential_help(e)
                if help_messages:
                    safe_print("")
                    for message in help_messages:
                        safe_print(message)
                
        else:
            safe_print(f"[red]❌ No valid AWS credentials found[/red]")
            if error:
                safe_print(f"[red]Error: {error}[/red]")
                
            safe_print("\n[yellow]Setup AWS credentials using one of:[/yellow]")
            safe_print("  • aws configure")
            safe_print("  • AWS SSO: aws sso login --profile <profile>")
            safe_print("  • Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            safe_print("  • IAM roles or EC2 instance profiles")
            
    except Exception as e:
        safe_print(f"[red]Error checking credentials: {e}[/red]")


@app.command()
def test():
    """Test AWS connectivity and credentials"""
    safe_print("[bold cyan]Testing AWS connectivity...[/bold cyan]")
    
    try:
        # Test credential detection
        has_creds, account_id, error = aws_session.check_credentials()
        
        if has_creds and account_id:
            credential_source = aws_session.detect_credential_source()
            safe_print(f"Credentials working: {credential_source}")
            safe_print(f"Account ID: {account_id}")
            
            # Test region detection
            import boto3
            session = boto3.Session()
            region = session.region_name or 'us-east-1'
            safe_print(f"Default region: {region}")
            
            # Test EC2 permissions
            safe_print("\nTesting EC2 permissions...")
            try:
                import asyncio
                responses = asyncio.run(aws_session.call_service_async(
                    'ec2', 
                    'describe_instances',
                    regions=[region]
                ))
                
                if responses:
                    instance_count = sum(
                        len(reservation['Instances']) 
                        for response in responses.values() 
                        for reservation in response.get('Reservations', [])
                    )
                    safe_print(f"EC2 API access working - found {instance_count} instances in {region}")
                else:
                    safe_print(f"EC2 API access working - no instances in {region}")
                    
            except Exception as e:
                safe_print(f"[yellow]API access test failed: {e}[/yellow]")
            
        elif has_creds and error:
            safe_print(f"Credentials found but invalid: {error}")
            help_messages = aws_session.get_credential_help(error)
            if help_messages:
                safe_print("")
                for message in help_messages:
                    safe_print(message)
        else:
            safe_print("No AWS credentials found")
            help_messages = aws_session.get_credential_help(Exception("NoCredentialsError"))
            for message in help_messages:
                safe_print(message)
                
    except Exception as e:
        safe_print(f"Unexpected error: {e}")


@app.command()
def accounts(
    health_check: bool = typer.Option(True, "--health-check/--no-health-check", help="Perform health checks on accounts"),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by account category"),
    show_details: bool = typer.Option(False, "--details", help="Show detailed account information")
):
    """List available AWS accounts with intelligent categorization and health checks
    
    Health Status: HEALTHY (all services accessible), WARNING (limited permissions), 
    ERROR (access issues), UNKNOWN (health check disabled).
    
    Run 'aws-super-cli accounts-health --explain' for detailed health criteria.
    """
    safe_print("[bold cyan]AWS Account Intelligence[/bold cyan]")
    safe_print()
    
    try:
        if health_check:
            safe_print("[dim]Discovering accounts and performing health checks...[/dim]")
        else:
            safe_print("[dim]Discovering accounts (skipping health checks for speed)...[/dim]")
        
        # Get enhanced account information
        async def get_accounts():
            return await account_intelligence.get_enhanced_accounts(include_health_check=health_check)
        
        enhanced_accounts = asyncio.run(get_accounts())
        
        if not enhanced_accounts:
            safe_print("[yellow]No AWS accounts found.[/yellow]")
            safe_print("\n[dim]Set up profiles with:[/dim]")
            safe_print("  aws configure --profile mycompany")
            safe_print("  aws configure sso")
            return
        
        # Filter by category if specified
        if category:
            try:
                filter_category = AccountCategory(category.lower())
                enhanced_accounts = [acc for acc in enhanced_accounts if acc.category == filter_category]
                
                if not enhanced_accounts:
                    safe_print(f"[yellow]No accounts found in category '{category}'[/yellow]")
                    return
            except ValueError:
                safe_print(f"[red]Invalid category '{category}'. Valid categories: {', '.join([c.value for c in AccountCategory])}[/red]")
                return
        
        # Create and display enhanced table
        table = account_intelligence.create_enhanced_accounts_table(enhanced_accounts)
        safe_print(table)
        
        # Summary statistics
        total_accounts = len(enhanced_accounts)
        healthy_accounts = len([acc for acc in enhanced_accounts if acc.health.value == 'healthy'])
        
        # Group by category for summary
        categorized = account_intelligence.get_accounts_by_category(enhanced_accounts)
        
        safe_print("\n[bold]Account Summary[/bold]")
        safe_print(f"Total Accounts: {total_accounts}")
        if health_check:
            safe_print(f"Healthy Accounts: [green]{healthy_accounts}[/green] / {total_accounts}")
        
        if len(categorized) > 1:
            safe_print("\n[bold]Categories:[/bold]")
            for cat, accounts in categorized.items():
                if cat == AccountCategory.PRODUCTION:
                    safe_print(f"  [red bold]{cat.value}[/red bold]: {len(accounts)} accounts")
                elif cat == AccountCategory.STAGING:
                    safe_print(f"  [yellow]{cat.value}[/yellow]: {len(accounts)} accounts")
                elif cat == AccountCategory.DEVELOPMENT:
                    safe_print(f"  [green]{cat.value}[/green]: {len(accounts)} accounts")
                else:
                    safe_print(f"  {cat.value}: {len(accounts)} accounts")
        
        # Enhanced usage examples
        safe_print("\n[bold]Multi-Account Operations:[/bold]")
        safe_print("  [cyan]aws-super-cli accounts --category production[/cyan]      # View production accounts only")
        safe_print("  [cyan]aws-super-cli accounts --no-health-check[/cyan]         # Fast account listing")
        safe_print("  [cyan]aws-super-cli accounts nickname[/cyan]                  # Manage account nicknames")
        safe_print()
        safe_print("  [cyan]aws-super-cli ls ec2 --all-accounts[/cyan]              # Query all accessible accounts")
        safe_print("  [cyan]aws-super-cli audit --all-accounts[/cyan]               # Security audit across accounts")
        safe_print("  [cyan]aws-super-cli ls s3 --accounts prod-*[/cyan]           # Query accounts by pattern")
        
        # Show example with actual profile names
        if len(enhanced_accounts) >= 2:
            example_profiles = [acc.name for acc in enhanced_accounts[:2]]
            safe_print(f"  [cyan]aws-super-cli ls vpc --accounts {','.join(example_profiles)}[/cyan] # Query specific accounts")
        
        # Health warnings
        if health_check:
            unhealthy_accounts = [acc for acc in enhanced_accounts if acc.health.value in ['warning', 'error']]
            if unhealthy_accounts:
                safe_print(f"\n[yellow]Health Issues Found[/yellow]")
                safe_print(f"Run [cyan]aws-super-cli accounts-health[/cyan] for detailed health information")
        
    except Exception as e:
        safe_print(f"[red]Error discovering accounts: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            safe_print("")
            for message in help_messages:
                safe_print(message)


@app.command(name="accounts-health", help="Detailed health information for AWS accounts")
def accounts_health(
    explain: bool = typer.Option(False, "--explain", help="Show detailed explanation of health check criteria"),
    details: bool = typer.Option(False, "--details", help="Show detailed health check breakdown for each account")
):
    """Show detailed health information for AWS accounts"""
    safe_print("[bold cyan]AWS Account Health Report[/bold cyan]")
    safe_print()
    
    if explain:
        # Show detailed health criteria explanation
        safe_print("[bold]Health Check Criteria Explanation[/bold]")
        safe_print()
        
        safe_print("[green bold]✓ HEALTHY[/green bold] - All checks pass:")
        safe_print("  ✓ Authentication successful (STS get_caller_identity)")
        safe_print("  ✓ EC2 service accessible (describe_regions)")
        safe_print("  ✓ IAM service accessible (get_account_summary)")
        safe_print("  ✓ S3 service accessible (list_buckets)")
        safe_print("  ✓ No permission restrictions detected")
        safe_print()
        
        safe_print("[yellow bold]⚠ WARNING[/yellow bold] - Limited permissions:")
        safe_print("  ✓ Basic authentication successful")
        safe_print("  ⚠ Some services have limited permissions")
        safe_print("  ⚠ AccessDenied or UnauthorizedOperation errors")
        safe_print("  ✓ No complete service failures")
        safe_print()
        
        safe_print("[red bold]✗ ERROR[/red bold] - Major access issues:")
        safe_print("  ✗ Authentication failures (NoCredentialsError)")
        safe_print("  ✗ Complete service access failures")
        safe_print("  ✗ Unable to perform basic operations")
        safe_print("  ✗ Invalid credentials or expired tokens")
        safe_print()
        
        safe_print("[dim bold]? UNKNOWN[/dim bold] - Health check not performed:")
        safe_print("  • Used when --no-health-check flag is specified")
        safe_print("  • Faster account listing without connectivity tests")
        safe_print()
        
        safe_print("[bold]Services Tested[/bold]")
        safe_print("  • [cyan]EC2[/cyan]: describe_regions() - Tests compute service access")
        safe_print("  • [cyan]IAM[/cyan]: get_account_summary() - Tests identity management")
        safe_print("  • [cyan]S3[/cyan]: list_buckets() - Tests storage service access")
        safe_print()
        
        safe_print("[bold]Troubleshooting[/bold]")
        safe_print("  [yellow]WARNING status[/yellow]: Check IAM policy permissions for restricted services")
        safe_print("  [red]ERROR status[/red]: Verify AWS credentials with 'aws sts get-caller-identity'")
        safe_print("  [dim]For specific issues, run 'aws-super-cli accounts-health --details' for more information[/dim]")
        safe_print()
        
        safe_print("[bold]Usage Examples[/bold]")
        safe_print("  [cyan]aws-super-cli accounts-health[/cyan]                    # Health report")
        safe_print("  [cyan]aws-super-cli accounts-health --explain[/cyan]          # This explanation")
        safe_print("  [cyan]aws-super-cli accounts-health --details[/cyan]          # Detailed health breakdown")
        safe_print("  [cyan]aws-super-cli accounts --no-health-check[/cyan]        # Fast listing")
        safe_print("  [cyan]aws-super-cli accounts --category production[/cyan]    # Filter unhealthy production")
        safe_print()
        return
    
    try:
        safe_print("[dim]Performing comprehensive health checks...[/dim]")
        
        async def get_health_report():
            accounts = await account_intelligence.get_enhanced_accounts(include_health_check=True)
            return accounts
        
        accounts = asyncio.run(get_health_report())
        
        if not accounts:
            safe_print("[yellow]No accounts found[/yellow]")
            return
        
        # Group by health status
        healthy = [acc for acc in accounts if acc.health.value == 'healthy']
        warning = [acc for acc in accounts if acc.health.value == 'warning']
        error = [acc for acc in accounts if acc.health.value == 'error']
        unknown = [acc for acc in accounts if acc.health.value == 'unknown']
        
        # Health summary
        safe_print(f"[bold]Health Summary:[/bold]")
        safe_print(f"  [green]Healthy: {len(healthy)}[/green]")
        safe_print(f"  [yellow]Warning: {len(warning)}[/yellow]")
        safe_print(f"  [red]Error: {len(error)}[/red]")
        safe_print(f"  [dim]Unknown: {len(unknown)}[/dim]")
        safe_print()
        
        # Show problematic accounts first
        if error:
            safe_print("[red bold]Accounts with Errors:[/red bold]")
            for account in error:
                safe_print(f"  [red]✗ {account.name}[/red] ({account.account_id})")
                safe_print(f"    Category: {account.category.value}")
                
                if details:
                    # Show detailed health check breakdown
                    health_details = account_intelligence.get_health_details(account.name)
                    if health_details:
                        safe_print("    Health Details:")
                        for detail in health_details:
                            safe_print(f"      {detail}")
            safe_print()
        
        if warning:
            safe_print("[yellow bold]Accounts with Warnings:[/yellow bold]")
            for account in warning:
                safe_print(f"  [yellow]⚠ {account.name}[/yellow] ({account.account_id})")
                safe_print(f"    Category: {account.category.value}")
                
                if details:
                    # Show detailed health check breakdown
                    health_details = account_intelligence.get_health_details(account.name)
                    if health_details:
                        safe_print("    Health Details:")
                        for detail in health_details:
                            safe_print(f"      {detail}")
            safe_print()
        
        if healthy:
            safe_print("[green bold]Healthy Accounts:[/green bold]")
            for account in healthy:
                if details:
                    safe_print(f"  [green]✓ {account.name}[/green] ({account.account_id}) - {account.category.value}")
                    # Show detailed health check breakdown
                    health_details = account_intelligence.get_health_details(account.name)
                    if health_details:
                        safe_print("    Health Details:")
                        for detail in health_details:
                            safe_print(f"      {detail}")
                else:
                    safe_print(f"  [green]✓ {account.name}[/green] ({account.account_id}) - {account.category.value}")
        
        # Recommendations
        safe_print("\n[bold]Recommendations:[/bold]")
        if error:
            safe_print("  [red]• Fix authentication issues for error accounts[/red]")
        if warning:
            safe_print("  [yellow]• Review permission configurations for warning accounts[/yellow]")
        if len(healthy) == len(accounts):
            safe_print("  [green]• All accounts are healthy![/green]")
        
    except Exception as e:
        safe_print(f"[red]Error generating health report: {e}[/red]")


@app.command(name="accounts-nickname", help="Manage account nicknames")
def accounts_nickname(
    profile: Optional[str] = typer.Argument(None, help="Profile name to set nickname for"),
    nickname: Optional[str] = typer.Argument(None, help="Nickname to set")
):
    """Manage account nicknames for easier identification"""
    
    if not profile:
        # Show current nicknames
        safe_print("[bold cyan]Account Nicknames[/bold cyan]")
        safe_print()
        
        nicknames = account_intelligence.load_nicknames()
        
        if not nicknames:
            safe_print("[yellow]No nicknames set[/yellow]")
            safe_print("\n[dim]Set a nickname with:[/dim]")
            safe_print("  aws-super-cli accounts-nickname myprofile \"My Company Prod\"")
            return
        
        # Show nicknames table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Profile", style="cyan", min_width=15)
        table.add_column("Nickname", style="green", min_width=20)
        
        for profile_name, nick in nicknames.items():
            table.add_row(profile_name, nick)
        
        safe_print(table)
        safe_print(f"\n[green]Found {len(nicknames)} nicknames[/green]")
        return
    
    if not nickname:
        safe_print(f"[red]Please provide a nickname for profile '{profile}'[/red]")
        safe_print(f"[dim]Example: aws-super-cli accounts-nickname {profile} \"My Company Production\"[/dim]")
        return
    
    # Set nickname
    try:
        account_intelligence.save_nickname(profile, nickname)
        safe_print(f"[green]Set nickname for '{profile}': [bold]{nickname}[/bold][/green]")
        safe_print(f"\n[dim]Run 'aws-super-cli accounts' to see the updated display[/dim]")
        
    except Exception as e:
        safe_print(f"[red]Error setting nickname: {e}[/red]")


@app.command(name="accounts-dashboard", help="Show comprehensive account dashboard with enhanced intelligence")
def accounts_dashboard():
    """Show comprehensive account dashboard with enhanced intelligence"""
    safe_print("[bold cyan]AWS Account Dashboard[/bold cyan]")
    safe_print()
    
    try:
        async def get_dashboard_data():
            return await account_intelligence.get_enhanced_accounts(include_health_check=True)
        
        accounts = asyncio.run(get_dashboard_data())
        
        if not accounts:
            safe_print("[yellow]No accounts found[/yellow]")
            return
        
        # Group by category for dashboard view
        categorized = account_intelligence.get_accounts_by_category(accounts)
        
        # Summary statistics
        total_accounts = len(accounts)
        healthy_accounts = len([acc for acc in accounts if acc.health.value == 'healthy'])
        
        safe_print(f"[bold]Total Accounts:[/bold] {total_accounts}")
        safe_print(f"[bold]Healthy Accounts:[/bold] [green]{healthy_accounts}[/green] / {total_accounts}")
        safe_print()
        
        # Category breakdown
        safe_print("[bold]Account Categories:[/bold]")
        for category, category_accounts in categorized.items():
            category_healthy = len([acc for acc in category_accounts if acc.health.value == 'healthy'])
            
            if category == AccountCategory.PRODUCTION:
                safe_print(f"  [red bold]{category.value.title()}:[/red bold] {len(category_accounts)} accounts ({category_healthy} healthy)")
            elif category == AccountCategory.STAGING:
                safe_print(f"  [yellow]{category.value.title()}:[/yellow] {len(category_accounts)} accounts ({category_healthy} healthy)")
            elif category == AccountCategory.DEVELOPMENT:
                safe_print(f"  [green]{category.value.title()}:[/green] {len(category_accounts)} accounts ({category_healthy} healthy)")
            else:
                safe_print(f"  {category.value.title()}: {len(category_accounts)} accounts ({category_healthy} healthy)")
        
        safe_print()
        
        # Show detailed table
        table = account_intelligence.create_enhanced_accounts_table(accounts)
        safe_print(table)
        
    except Exception as e:
        safe_print(f"[red]Error generating dashboard: {e}[/red]")


@app.command(name="accounts-organizations", help="AWS Organizations integration for large-scale account discovery")
def accounts_organizations(
    profile: Optional[str] = typer.Option(None, "--profile", help="AWS profile to use for Organizations API access"),
    show_ous: bool = typer.Option(False, "--show-ous", help="Show organizational unit structure"),
    export_csv: Optional[str] = typer.Option(None, "--export-csv", help="Export accounts to CSV file"),
    health_check: bool = typer.Option(False, "--health-check", help="Perform health checks (slower for large organizations)")
):
    """Discover and manage accounts via AWS Organizations API
    
    This command provides large-scale account discovery for organizations with hundreds of AWS accounts.
    It uses the AWS Organizations API to discover all accounts and their organizational structure.
    
    Requirements:
    - Access to AWS Organizations API (management account or delegated admin)
    - organizations:ListAccounts permission
    - organizations:ListOrganizationalUnitsForParent permission (for OU structure)
    """
    safe_print("[bold cyan]AWS Organizations Account Discovery[/bold cyan]")
    safe_print()
    
    try:
        safe_print("[dim]Discovering organization structure and accounts...[/dim]")
        
        async def discover_org_accounts():
            # Try to discover via Organizations API
            org_accounts, ous = await account_intelligence.discover_organization_accounts(profile)
            
            if not org_accounts:
                safe_print("[yellow]No AWS Organizations found or insufficient permissions[/yellow]")
                safe_print("\n[dim]Requirements:[/dim]")
                safe_print("  • Access to AWS Organizations management account")
                safe_print("  • organizations:ListAccounts permission")
                safe_print("  • organizations:ListOrganizationalUnitsForParent permission")
                safe_print("\n[dim]Alternative: Use 'aws-super-cli accounts' for profile-based discovery[/dim]")
                return [], []
            
            return org_accounts, ous
        
        org_accounts, ous = asyncio.run(discover_org_accounts())
        
        if not org_accounts:
            return
        
        safe_print(f"[green]Found {len(org_accounts)} accounts in organization[/green]")
        if ous:
            safe_print(f"[green]Found {len(ous)} organizational units[/green]")
        safe_print()
        
        # Show OU structure if requested
        if show_ous and ous:
            safe_print("[bold]Organizational Unit Structure:[/bold]")
            
            # Group OUs by parent for hierarchical display
            root_ous = [ou for ou in ous if not ou.parent_id or ou.parent_id.startswith('r-')]
            
            def display_ou_tree(parent_ous, indent=0):
                for ou in sorted(parent_ous, key=lambda x: x.name):
                    prefix = "  " * indent + "├─ " if indent > 0 else ""
                    safe_print(f"{prefix}[blue]{ou.name}[/blue] ({ou.id})")
                    
                    # Find child OUs
                    child_ous = [child_ou for child_ou in ous if child_ou.parent_id == ou.id]
                    if child_ous:
                        display_ou_tree(child_ous, indent + 1)
            
            display_ou_tree(root_ous)
            safe_print()
        
        # Get enhanced account profiles with Organizations data
        async def get_enhanced_org_accounts():
            return await account_intelligence.get_enhanced_accounts(
                include_health_check=health_check,
                include_organizations=True
            )
        
        enhanced_accounts = asyncio.run(get_enhanced_org_accounts())
        
        # Filter to only show accounts that were discovered via Organizations
        org_enhanced_accounts = [acc for acc in enhanced_accounts if acc.organization_account]
        
        if not org_enhanced_accounts:
            safe_print("[yellow]No enhanced account data available[/yellow]")
            return
        
        # Display accounts table
        table = account_intelligence.create_enhanced_accounts_table(org_enhanced_accounts)
        safe_print(table)
        
        # Summary statistics
        total_accounts = len(org_enhanced_accounts)
        active_accounts = len([acc for acc in org_enhanced_accounts if acc.status == 'active'])
        
        # Group by category
        categorized = account_intelligence.get_accounts_by_category(org_enhanced_accounts)
        
        safe_print("\n[bold]Organization Summary[/bold]")
        safe_print(f"Total Accounts: {total_accounts}")
        safe_print(f"Active Accounts: [green]{active_accounts}[/green] / {total_accounts}")
        
        if health_check:
            healthy_accounts = len([acc for acc in org_enhanced_accounts if acc.health.value == 'healthy'])
            safe_print(f"Healthy Accounts: [green]{healthy_accounts}[/green] / {total_accounts}")
        
        if len(categorized) > 1:
            safe_print("\n[bold]Categories:[/bold]")
            for cat, accounts in categorized.items():
                if cat == AccountCategory.PRODUCTION:
                    safe_print(f"  [red bold]{cat.value}[/red bold]: {len(accounts)} accounts")
                elif cat == AccountCategory.STAGING:
                    safe_print(f"  [yellow]{cat.value}[/yellow]: {len(accounts)} accounts")
                elif cat == AccountCategory.DEVELOPMENT:
                    safe_print(f"  [green]{cat.value}[/green]: {len(accounts)} accounts")
                else:
                    safe_print(f"  {cat.value}: {len(accounts)} accounts")
        
        # Export to CSV if requested
        if export_csv:
            try:
                import csv
                with open(export_csv, 'w', newline='') as csvfile:
                    fieldnames = ['account_id', 'name', 'email', 'category', 'status', 'organizational_units', 'health']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for account in org_enhanced_accounts:
                        ou_names = ', '.join([ou.name for ou in account.organizational_units]) if account.organizational_units else 'Root'
                        writer.writerow({
                            'account_id': account.account_id,
                            'name': account.name,
                            'email': account.organization_account.email if account.organization_account else '',
                            'category': account.category.value,
                            'status': account.status,
                            'organizational_units': ou_names,
                            'health': account.health.value
                        })
                
                safe_print(f"\n[green]Exported {len(org_enhanced_accounts)} accounts to {export_csv}[/green]")
            except Exception as e:
                safe_print(f"\n[red]Error exporting to CSV: {e}[/red]")
        
        # Usage examples
        safe_print("\n[bold]Large-Scale Operations:[/bold]")
        safe_print("  [cyan]aws-super-cli accounts-organizations --show-ous[/cyan]           # Show OU structure")
        safe_print("  [cyan]aws-super-cli accounts-organizations --health-check[/cyan]       # Include health checks")
        safe_print("  [cyan]aws-super-cli accounts-organizations --export-csv org.csv[/cyan] # Export to CSV")
        safe_print("  [cyan]aws-super-cli audit --all-accounts[/cyan]                       # Security audit across organization")
        
    except Exception as e:
        safe_print(f"[red]Error discovering organization accounts: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            safe_print("")
            for message in help_messages:
                safe_print(message)


@app.command()
def audit(
    services: Optional[str] = typer.Option("s3,iam,network,compute,guardduty,config,cloudtrail,rds,cloudwatch", "--services", help="Comma-separated services to audit (s3, iam, network, compute, guardduty, config, cloudtrail, rds, cloudwatch)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Specific region to query"),
    all_regions: bool = typer.Option(True, "--all-regions/--no-all-regions", help="Query all regions (default) or current region only"),
    all_accounts: bool = typer.Option(False, "--all-accounts", help="Query all accessible AWS accounts"),
    accounts: Optional[str] = typer.Option(None, "--accounts", help="Comma-separated profiles or pattern (e.g., 'prod-*,staging')"),
    summary_only: bool = typer.Option(False, "--summary", help="Show only summary statistics"),
    export_format: Optional[str] = typer.Option(None, "--export", help="Export format: csv, txt, html, enhanced-html"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: auto-generated)"),
):
    """Run security audit to identify misconfigurations and threats (includes GuardDuty findings)"""
    
    # Parse services
    service_list = [s.strip().lower() for s in services.split(',')]
    
    # Determine which profiles/accounts to query
    profiles_to_query = []
    
    if all_accounts:
        # Query all accessible accounts
        try:
            accounts_info = asyncio.run(aws_session.multi_account.discover_accounts())
            profiles_to_query = [acc['profile'] for acc in accounts_info]
            
            if not profiles_to_query:
                safe_print("[yellow]No accessible AWS accounts found.[/yellow]")
                safe_print("\n[dim]Run 'aws-super-cli accounts' to see available profiles[/dim]")
                return
                
            safe_print(f"[dim]Auditing {len(profiles_to_query)} accounts: {', '.join(profiles_to_query)}[/dim]")
            
        except Exception as e:
            safe_print(f"[red]Error discovering accounts: {e}[/red]")
            return
    elif accounts:
        # Query specific accounts or patterns
        if ',' in accounts:
            # Multiple accounts specified
            account_patterns = [p.strip() for p in accounts.split(',')]
        else:
            # Single account or pattern
            account_patterns = [accounts.strip()]
        
        # Expand patterns
        for pattern in account_patterns:
            if '*' in pattern:
                # Pattern matching
                matched = aws_session.multi_account.get_profiles_by_pattern(pattern.replace('*', ''))
                profiles_to_query.extend(matched)
            else:
                # Exact profile name
                profiles_to_query.append(pattern)
        
        if not profiles_to_query:
            safe_print(f"[yellow]No profiles found matching: {accounts}[/yellow]")
            safe_print("\n[dim]Run 'aws-super-cli accounts' to see available profiles[/dim]")
            return
            
        safe_print(f"[dim]Auditing accounts: {', '.join(profiles_to_query)}[/dim]")
    else:
        # Single account (current profile)
        profiles_to_query = None  # Will use current profile by default
        safe_print("[dim]Auditing current account...[/dim]")
    
    # Determine regions to query
    if region:
        regions_to_query = [region]
    elif all_regions:
        regions_to_query = aws_session.get_available_regions('s3')  # Use S3 regions as base
    else:
        # Current region only
        try:
            import boto3
            session = boto3.Session()
            current_region = session.region_name or 'us-east-1'
            regions_to_query = [current_region]
        except:
            regions_to_query = ['us-east-1']
    
    try:
        # Run the security audit
        findings = asyncio.run(audit_service.run_security_audit(
            services=service_list,
            regions=regions_to_query,
            all_regions=all_regions,
            profiles=profiles_to_query
        ))
        
        # Generate summary
        summary = audit_service.get_security_summary(findings)
        
        if summary_only or not findings:
            # Show summary only
            safe_print(f"\n[bold]Security Audit Summary[/bold]")
            safe_print(f"Security Score: [{'red' if summary['score'] < 70 else 'yellow' if summary['score'] < 90 else 'green'}]{summary['score']}/100[/]")
            safe_print(f"Total Findings: {summary['total']}")
            
            if summary['total'] > 0:
                safe_print(f"  High Risk: [red]{summary['high']}[/red]")
                safe_print(f"  Medium Risk: [yellow]{summary['medium']}[/yellow]")
                safe_print(f"  Low Risk: [green]{summary['low']}[/green]")
                
                # Show breakdown by service
                safe_print(f"\nFindings by Service:")
                for service, count in summary['services'].items():
                    safe_print(f"  {service}: {count}")
            else:
                safe_print("[green]No security issues found[/green]")
            
            return
        
        # Show detailed findings
        show_account = profiles_to_query is not None and len(profiles_to_query) > 1
        
        # Handle export options
        if export_format:
            # Validate export format
            if export_format.lower() not in ['csv', 'txt', 'html', 'enhanced-html']:
                safe_print(f"[red]Error: Unsupported export format '{export_format}'. Supported formats: csv, txt, html, enhanced-html[/red]")
                return
            
            # Generate output filename if not provided
            if not output_file:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ext = 'html' if export_format.lower() == 'enhanced-html' else export_format.lower()
                output_file = f"aws_security_audit_{timestamp}.{ext}"
            
            # Ensure the filename has the correct extension
            elif export_format.lower() == 'enhanced-html':
                if not output_file.lower().endswith('.html'):
                    output_file = f"{output_file}.html"
            elif not output_file.lower().endswith(f'.{export_format.lower()}'):
                output_file = f"{output_file}.{export_format.lower()}"
            
            # Export the findings
            try:
                if export_format.lower() == 'csv':
                    audit_service.export_findings_csv(findings, output_file, show_account=show_account)
                elif export_format.lower() == 'txt':
                    audit_service.export_findings_txt(findings, output_file, show_account=show_account)
                elif export_format.lower() == 'html':
                    audit_service.export_findings_html(findings, output_file, show_account=show_account)
                elif export_format.lower() == 'enhanced-html':
                    from aws_super_cli.services.enhanced_reporting import EnhancedSecurityReporter
                    reporter = EnhancedSecurityReporter()
                    reporter.export_enhanced_html_report(findings, output_file, show_account=show_account)
                
                safe_print(f"[green]Audit results exported to: {output_file}[/green]")
                
                # Show summary in terminal as well
                safe_print(f"\n[bold]Security Summary[/bold]")
                safe_print(f"Security Score: [{'red' if summary['score'] < 70 else 'yellow' if summary['score'] < 90 else 'green'}]{summary['score']}/100[/]")
                safe_print(f"Found {summary['total']} security findings:")
                safe_print(f"  [red]High Risk: {summary['high']}[/red]")
                safe_print(f"  [yellow]Medium Risk: {summary['medium']}[/yellow]")
                safe_print(f"  [green]Low Risk: {summary['low']}[/green]")
                
                return
                
            except Exception as export_error:
                safe_print(f"[red]Error exporting results: {export_error}[/red]")
                # Continue with normal output if export fails
        
        table = audit_service.create_audit_table(findings, show_account=show_account)
        safe_print(table)
        
        # Show summary at the end
        safe_print(f"\n[bold]Security Summary[/bold]")
        safe_print(f"Security Score: [{'red' if summary['score'] < 70 else 'yellow' if summary['score'] < 90 else 'green'}]{summary['score']}/100[/]")
        safe_print(f"Found {summary['total']} security findings:")
        safe_print(f"  [red]High Risk: {summary['high']}[/red]")
        safe_print(f"  [yellow]Medium Risk: {summary['medium']}[/yellow]")
        safe_print(f"  [green]Low Risk: {summary['low']}[/green]")
        
        # Recommendations
        if summary['high'] > 0:
            safe_print(f"\n[red]PRIORITY: Address {summary['high']} high-risk findings immediately[/red]")
        elif summary['medium'] > 0:
            safe_print(f"\n[yellow]RECOMMENDED: Review {summary['medium']} medium-risk findings[/yellow]")
        else:
            safe_print(f"\n[green]Account security looks good! Consider reviewing {summary['low']} low-risk items[/green]")
            
        if profiles_to_query:
            account_count = len(profiles_to_query)
            safe_print(f"\n[dim]Audit completed across {account_count} accounts[/dim]")
        
    except Exception as e:
        safe_print(f"[red]Error running security audit: {e}[/red]")
        if "--debug" in str(e):
            import traceback
            safe_print(f"[dim]{traceback.format_exc()}[/dim]")


@app.command(name="help", help="Show help information and common examples")
def help_command():
    """Show help information"""
    
    # Detect if we should use clean output (no Rich markup)
    # This is important for tests and environments where Rich markup should not leak
    use_clean_output = should_use_clean_output()
    
    if use_clean_output:
        # Clean output without Rich markup
        print()
        print("AWS Super CLI - Quick Reference")
        print()
        print("Most Common Commands:")
        print("  aws-super-cli ls ec2                    # List EC2 instances")
        print("  aws-super-cli ls s3                     # List S3 buckets") 
        print("  aws-super-cli audit                     # Run security audit")
        print("  aws-super-cli accounts                  # Show available accounts")
        print("  aws-super-cli cost summary              # Cost overview")
        print()
        print("Resource Discovery:")
        print("  aws-super-cli ls ec2 --all-accounts     # EC2 across all accounts")
        print("  aws-super-cli ls rds --engine postgres  # Find PostgreSQL databases")
        print("  aws-super-cli ls lambda --runtime python # Find Python functions")
        print()
        print("Security Auditing:")
        print("  aws-super-cli audit --summary           # Quick security overview")
        print("  aws-super-cli audit --all-accounts      # Audit all accounts")
        print("  aws-super-cli audit --services network  # Network security only")
        print("  aws-super-cli audit --services s3,iam   # S3 and IAM audit only")
        print("  aws-super-cli audit --services guardduty # GuardDuty threat detection")
        print("  aws-super-cli audit --export csv        # Export results to CSV")
        print("  aws-super-cli audit --export html       # Export results to HTML")
        print("  aws-super-cli audit --export enhanced-html # Enhanced HTML with executive summary")
        print("  aws-super-cli audit --export txt -o report.txt # Export to specific file")
        print()
        print("ARN Intelligence:")
        print("  aws-super-cli explain arn:aws:iam::123:user/john # Explain an ARN")
        print("  aws-super-cli ls iam --show-full-arns    # Show full ARNs")
        print("  aws-super-cli ls iam                     # Smart ARN display (default)")
        print()
        print("Cost Analysis:")
        print("  aws-super-cli cost summary              # Overall cost trends")
        print("  aws-super-cli cost top-spend            # Biggest cost services")
        print("  aws-super-cli cost credits              # Credit usage analysis")
        print()
        print("Cost Optimization:")
        print("  aws-super-cli optimization-readiness    # Check prerequisites")
        print("  aws-super-cli optimization-recommendations # Get cost recommendations")
        print("  aws-super-cli cost-snapshot             # Comprehensive cost analysis")
        print()
        print("Multi-Account Intelligence:")
        print("  aws-super-cli accounts                   # Smart account categorization & health")
        print("  aws-super-cli accounts --category production # Filter by category") 
        print("  aws-super-cli accounts-dashboard         # Comprehensive account overview")
        print("  aws-super-cli accounts-health            # Detailed health report")
        print("  aws-super-cli accounts-health --explain   # Health criteria explanation")
        print("  aws-super-cli accounts-health --details   # Health check breakdown")
        print("  aws-super-cli accounts-nickname myprofile \"Name\" # Set account nicknames")
        print()
        print("For detailed help:")
        print("  aws-super-cli --help                    # Full command reference")
        print("  aws-super-cli ls --help                 # Resource listing help")
        print("  aws-super-cli audit --help              # Security audit help")
        print("  aws-super-cli cost --help               # Cost analysis help")
        print()
    else:
        # Rich output for interactive terminals
        safe_print()
        safe_print("[bold]AWS Super CLI - Quick Reference[/bold]")
        safe_print()
        safe_print("[bold]Most Common Commands:[/bold]")
        safe_print("  [cyan]aws-super-cli ls ec2[/cyan]                    # List EC2 instances")
        safe_print("  [cyan]aws-super-cli ls s3[/cyan]                     # List S3 buckets") 
        safe_print("  [cyan]aws-super-cli audit[/cyan]                     # Run security audit")
        safe_print("  [cyan]aws-super-cli accounts[/cyan]                  # Show available accounts")
        safe_print("  [cyan]aws-super-cli cost summary[/cyan]              # Cost overview")
        safe_print()
        safe_print("[bold]Resource Discovery:[/bold]")
        safe_print("  [cyan]aws-super-cli ls ec2 --all-accounts[/cyan]     # EC2 across all accounts")
        safe_print("  [cyan]aws-super-cli ls rds --engine postgres[/cyan]  # Find PostgreSQL databases")
        safe_print("  [cyan]aws-super-cli ls lambda --runtime python[/cyan] # Find Python functions")
        safe_print()
        safe_print("[bold]Security Auditing:[/bold]")
        safe_print("  [cyan]aws-super-cli audit --summary[/cyan]           # Quick security overview")
        safe_print("  [cyan]aws-super-cli audit --all-accounts[/cyan]      # Audit all accounts")
        safe_print("  [cyan]aws-super-cli audit --services network[/cyan]  # Network security only")
        safe_print("  [cyan]aws-super-cli audit --services s3,iam[/cyan]   # S3 and IAM audit only")
        safe_print("  [cyan]aws-super-cli audit --services guardduty[/cyan] # GuardDuty threat detection")
        safe_print("  [cyan]aws-super-cli audit --export csv[/cyan]        # Export results to CSV")
        safe_print("  [cyan]aws-super-cli audit --export html[/cyan]       # Export results to HTML")
        safe_print("  [cyan]aws-super-cli audit --export enhanced-html[/cyan] # Enhanced HTML with executive summary")
        safe_print("  [cyan]aws-super-cli audit --export txt -o report.txt[/cyan] # Export to specific file")
        safe_print()
        safe_print("[bold]ARN Intelligence:[/bold]")
        safe_print("  [cyan]aws-super-cli explain arn:aws:iam::123:user/john[/cyan] # Explain an ARN")
        safe_print("  [cyan]aws-super-cli ls iam --show-full-arns[/cyan]    # Show full ARNs")
        safe_print("  [cyan]aws-super-cli ls iam[/cyan]                     # Smart ARN display (default)")
        safe_print()
        safe_print("[bold]Cost Analysis:[/bold]")
        safe_print("  [cyan]aws-super-cli cost summary[/cyan]              # Overall cost trends")
        safe_print("  [cyan]aws-super-cli cost top-spend[/cyan]            # Biggest cost services")
        safe_print("  [cyan]aws-super-cli cost credits[/cyan]              # Credit usage analysis")
        safe_print()
        safe_print("[bold]Cost Optimization:[/bold]")
        safe_print("  [cyan]aws-super-cli optimization-readiness[/cyan]    # Check prerequisites")
        safe_print("  [cyan]aws-super-cli optimization-recommendations[/cyan] # Get cost recommendations")
        safe_print("  [cyan]aws-super-cli cost-snapshot[/cyan]             # Comprehensive cost analysis")
        safe_print()
        safe_print("[bold]Multi-Account Intelligence:[/bold]")
        safe_print("  [cyan]aws-super-cli accounts[/cyan]                   # Smart account categorization & health")
        safe_print("  [cyan]aws-super-cli accounts --category production[/cyan] # Filter by category") 
        safe_print("  [cyan]aws-super-cli accounts-dashboard[/cyan]         # Comprehensive account overview")
        safe_print("  [cyan]aws-super-cli accounts-health[/cyan]            # Detailed health report")
        safe_print("  [cyan]aws-super-cli accounts-health --explain[/cyan]  # Health criteria explanation")
        safe_print("  [cyan]aws-super-cli accounts-health --details[/cyan]  # Health check breakdown")
        safe_print("  [cyan]aws-super-cli accounts-nickname myprofile \"Name\"[/cyan] # Set account nicknames")
        safe_print()
        safe_print("[bold]For detailed help:[/bold]")
        safe_print("  [cyan]aws-super-cli --help[/cyan]                    # Full command reference")
        safe_print("  [cyan]aws-super-cli ls --help[/cyan]                 # Resource listing help")
        safe_print("  [cyan]aws-super-cli audit --help[/cyan]              # Security audit help")
        safe_print("  [cyan]aws-super-cli cost --help[/cyan]               # Cost analysis help")
        safe_print()


@app.command(name="explain", help="Explain AWS ARNs and break them down into components")
def explain_arn(
    arn: str = typer.Argument(..., help="ARN to explain (e.g., arn:aws:iam::123:user/john)")
):
    """Explain an AWS ARN and break it down into components"""
    
    if not arn.startswith('arn:'):
        safe_print(f"[red]Error: '{arn}' does not appear to be a valid ARN[/red]")
        safe_print()
        safe_print("[bold]ARN format:[/bold]")
        safe_print("  arn:partition:service:region:account:resource")
        safe_print()
        safe_print("[bold]Examples:[/bold]")
        safe_print("  [cyan]aws-super-cli explain arn:aws:iam::123456789012:user/john[/cyan]")
        safe_print("  [cyan]aws-super-cli explain arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0[/cyan]")
        safe_print("  [cyan]aws-super-cli explain arn:aws:s3:::my-bucket[/cyan]")
        return
    
    # Parse and explain the ARN
    explanation = arn_intelligence.explain_arn(arn)
    
    if "error" in explanation:
        safe_print(f"[red]Error: {explanation['error']}[/red]")
        return
    
    # Create a beautiful explanation table
    table = Table(title="ARN Breakdown", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", min_width=15)
    table.add_column("Value", style="green", min_width=20)
    table.add_column("Description", style="dim", min_width=30)
    
    # Add rows for each component
    for component, details in explanation.items():
        if component == "ARN":
            continue  # Skip the full ARN row
        
        # Split the details into value and description
        if " (" in details and details.endswith(")"):
            value, description = details.split(" (", 1)
            description = description.rstrip(")")
        else:
            value = details
            description = ""
        
        table.add_row(component, value, description)
    
    safe_print()
    safe_print(table)
    safe_print()
    
    # Show the human-readable version
    human_name = arn_intelligence.get_human_readable_name(arn)
    safe_print(f"[bold]Human-readable name:[/bold] [green]{human_name}[/green]")
    
    # Show smart truncated versions
    safe_print()
    safe_print("[bold]Display options:[/bold]")
    safe_print(f"  Short (20 chars): [yellow]{arn_intelligence.smart_truncate(arn, 20)}[/yellow]")
    safe_print(f"  Medium (30 chars): [yellow]{arn_intelligence.smart_truncate(arn, 30)}[/yellow]")
    safe_print(f"  Long (50 chars): [yellow]{arn_intelligence.smart_truncate(arn, 50)}[/yellow]")
    safe_print()


@app.command(name="optimization-readiness", help="Check prerequisites for AWS cost optimization features")
def optimization_readiness():
    """Check prerequisites for cost optimization features"""
    from .services.cost_optimization import cost_optimization_core
    from .services.trusted_advisor import trusted_advisor
    
    async def check_readiness():
        safe_print()
        safe_print("[bold]AWS Cost Optimization - Prerequisites Check[/bold]")
        safe_print()
        
        # Get account info
        account_info = await cost_optimization_core.get_account_info()
        
        # Check required IAM policies
        required_policies = [
            "AWSSupportAccess",
            "ComputeOptimizerReadOnlyAccess"
        ]
        iam_results = await cost_optimization_core.check_iam_permissions(required_policies)
        
        # Check support plan using both methods
        support_info = await cost_optimization_core.check_support_plan()
        
        # Also check Trusted Advisor access directly
        ta_access = await trusted_advisor.check_support_plan_access()
        
        # Check Compute Optimizer enrollment status
        from .services.compute_optimizer import compute_optimizer
        co_status = await compute_optimizer.check_enrollment_status()
        
        # Create and display prerequisites table
        table = cost_optimization_core.create_prerequisites_table(
            account_info, iam_results, support_info
        )
        safe_print(table)
        
        # Additional service-specific information
        safe_print()
        safe_print("[bold]Trusted Advisor Status[/bold]")
        if ta_access.get('has_access'):
            safe_print(f"[green]✓ Support Plan: {ta_access.get('support_plan')}[/green]")
            safe_print(f"[green]✓ Available Checks: {ta_access.get('checks_available', 0)}[/green]")
            safe_print(f"[dim]{ta_access.get('message')}[/dim]")
        else:
            safe_print(f"[yellow]⚠ Support Plan: {ta_access.get('support_plan')}[/yellow]")
            safe_print(f"[yellow]✗ {ta_access.get('message')}[/yellow]")
            if ta_access.get('error_code') == 'SUBSCRIPTION_REQUIRED':
                safe_print("[dim]Upgrade to Business or Enterprise support plan to access Trusted Advisor[/dim]")
        
        safe_print()
        safe_print("[bold]Compute Optimizer Status[/bold]")
        if co_status.get('enrolled'):
            safe_print(f"[green]✓ Status: {co_status.get('status')}[/green]")
            safe_print(f"[green]✓ Member Accounts: {co_status.get('member_accounts_enrolled')}[/green]")
            safe_print(f"[dim]{co_status.get('message')}[/dim]")
        else:
            safe_print(f"[yellow]⚠ Status: {co_status.get('status')}[/yellow]")
            safe_print(f"[yellow]✗ {co_status.get('message')}[/yellow]")
            if co_status.get('error_code') == 'ACCESS_DENIED':
                safe_print("[dim]Attach ComputeOptimizerReadOnlyAccess IAM policy to access Compute Optimizer[/dim]")
            elif co_status.get('status') == 'Inactive':
                safe_print("[dim]Compute Optimizer can be automatically activated when running recommendations[/dim]")
        
        # Provide guidance based on results
        safe_print()
        missing_requirements = []
        
        if account_info.get('account_id') == 'unknown':
            missing_requirements.append("AWS credentials not configured")
        
        for policy, has_permission in iam_results.items():
            if not has_permission:
                policy_name = policy.split('/')[-1] if '/' in policy else policy
                missing_requirements.append(f"IAM policy: {policy_name}")
        
        if not ta_access.get('has_access'):
            missing_requirements.append("Business or Enterprise support plan for Trusted Advisor")
        
        if not co_status.get('enrolled') and co_status.get('error_code') == 'ACCESS_DENIED':
            missing_requirements.append("ComputeOptimizerReadOnlyAccess IAM policy")
        
        if missing_requirements:
            safe_print("[yellow]Missing Requirements:[/yellow]")
            for req in missing_requirements:
                safe_print(f"  ✗ {req}")
            safe_print()
            safe_print("[bold]Next Steps:[/bold]")
            safe_print("1. Ensure AWS credentials are configured")
            safe_print("2. Attach required IAM policies to your user/role")
            safe_print("3. Upgrade to Business or Enterprise support plan for Trusted Advisor")
            safe_print()
            safe_print("For detailed setup instructions:")
            safe_print("  aws-super-cli help")
        else:
            safe_print("[green]✓ All prerequisites met! Ready for cost optimization.[/green]")
            safe_print()
            safe_print("Available commands:")
            safe_print("  aws-super-cli optimization-recommendations  # Get cost recommendations")
            safe_print("  aws-super-cli cost-snapshot                # Comprehensive cost analysis")
    
    asyncio.run(check_readiness())


@app.command(name="optimization-recommendations", help="Get AWS cost optimization recommendations")
def optimization_recommendations(
    service: Optional[str] = typer.Option(None, "--service", help="Specific service (trusted-advisor, compute-optimizer, cost-explorer)"),
    all_services: bool = typer.Option(True, "--all-services/--no-all-services", help="Get recommendations from all available services"),
    export: bool = typer.Option(True, "--export/--no-export", help="Export recommendations to files"),
):
    """Get cost optimization recommendations from AWS services"""
    from .services.cost_optimization import cost_optimization_core, OptimizationRecommendation, handle_optimization_error
    from .services.trusted_advisor import trusted_advisor
    
    async def get_recommendations():
        safe_print()
        safe_print("[bold]AWS Cost Optimization - Recommendations[/bold]")
        safe_print()
        
        # Check prerequisites first
        account_info = await cost_optimization_core.get_account_info()
        if account_info.get('account_id') == 'unknown':
            safe_print("[red]Error: AWS credentials not configured[/red]")
            safe_print("Run: aws-super-cli optimization-readiness")
            return
        
        safe_print(f"[dim]Account: {account_info.get('account_id')}[/dim]")
        safe_print()
        
        all_recommendations = []
        
        # Determine which services to query
        services_to_query = []
        if service:
            if service.lower() == "trusted-advisor":
                services_to_query = ["trusted-advisor"]
            elif service.lower() == "compute-optimizer":
                services_to_query = ["compute-optimizer"]
            elif service.lower() == "cost-explorer":
                services_to_query = ["cost-explorer"]
            else:
                safe_print(f"[red]Unknown service: {service}[/red]")
                safe_print("Available services: trusted-advisor, compute-optimizer, cost-explorer")
                return
        elif all_services:
            services_to_query = ["trusted-advisor", "compute-optimizer", "cost-explorer"]
        else:
            services_to_query = ["trusted-advisor"]  # Default to Trusted Advisor
        
        # Get Trusted Advisor recommendations
        if "trusted-advisor" in services_to_query:
            safe_print("[bold]Trusted Advisor Integration[/bold]")
            try:
                # First check support plan access
                access_check = await trusted_advisor.check_support_plan_access()
                
                if access_check.get('has_access'):
                    safe_print(f"[green]✓ Support Plan: {access_check.get('support_plan')}[/green]")
                    safe_print(f"[dim]Available checks: {access_check.get('checks_available', 0)}[/dim]")
                    
                    # Get recommendations
                    ta_recommendations = await trusted_advisor.get_cost_optimization_recommendations()
                    all_recommendations.extend(ta_recommendations)
                    
                    if ta_recommendations:
                        # Show Trusted Advisor summary
                        ta_table = trusted_advisor.create_trusted_advisor_summary_table(ta_recommendations)
                        safe_print(ta_table)
                        safe_print()
                    else:
                        safe_print("[yellow]No Trusted Advisor recommendations found[/yellow]")
                        safe_print("[dim]This indicates your resources are well-optimized![/dim]")
                        safe_print()
                else:
                    safe_print(f"[yellow]⚠ Support Plan: {access_check.get('support_plan')}[/yellow]")
                    safe_print(f"[yellow]{access_check.get('message')}[/yellow]")
                    if access_check.get('error_code') == 'SUBSCRIPTION_REQUIRED':
                        safe_print("[dim]Upgrade to Business or Enterprise support plan to access Trusted Advisor[/dim]")
                    safe_print()
                    
            except Exception as e:
                handle_optimization_error(e, "Trusted Advisor")
                safe_print()
        
        # Get Compute Optimizer recommendations
        if "compute-optimizer" in services_to_query:
            safe_print("[bold]Compute Optimizer Integration[/bold]")
            try:
                from .services.compute_optimizer import compute_optimizer
                
                # First check enrollment status
                enrollment_status = await compute_optimizer.check_enrollment_status()
                
                if enrollment_status.get('enrolled'):
                    safe_print(f"[green]✓ Status: {enrollment_status.get('status')}[/green]")
                    safe_print(f"[dim]Member accounts enrolled: {enrollment_status.get('member_accounts_enrolled')}[/dim]")
                    
                    # Get recommendations
                    co_recommendations = await compute_optimizer.get_all_recommendations()
                    all_recommendations.extend(co_recommendations)
                    
                    if co_recommendations:
                        # Show Compute Optimizer summary
                        co_table = compute_optimizer.create_compute_optimizer_summary_table(co_recommendations)
                        safe_print(co_table)
                        safe_print()
                    else:
                        safe_print("[yellow]No Compute Optimizer recommendations found[/yellow]")
                        safe_print("[dim]This indicates your compute resources are well-optimized![/dim]")
                        safe_print()
                else:
                    safe_print(f"[yellow]⚠ Status: {enrollment_status.get('status')}[/yellow]")
                    safe_print(f"[yellow]{enrollment_status.get('message')}[/yellow]")
                    
                    if enrollment_status.get('error_code') == 'ACCESS_DENIED':
                        safe_print("[dim]Attach ComputeOptimizerReadOnlyAccess IAM policy to access Compute Optimizer[/dim]")
                    elif enrollment_status.get('status') == 'Inactive':
                        safe_print("[dim]Attempting to activate Compute Optimizer enrollment...[/dim]")
                        activation_result = await compute_optimizer.activate_enrollment()
                        if activation_result.get('success'):
                            safe_print(f"[green]✓ {activation_result.get('message')}[/green]")
                            safe_print("[dim]Note: It may take up to 24 hours for recommendations to appear[/dim]")
                        else:
                            safe_print(f"[yellow]✗ {activation_result.get('message')}[/yellow]")
                    safe_print()
                    
            except Exception as e:
                handle_optimization_error(e, "Compute Optimizer")
                safe_print()
        
        # Get Cost Explorer recommendations
        if "cost-explorer" in services_to_query:
            safe_print("[bold]Cost Explorer Integration[/bold]")
            try:
                from .services.cost_explorer import cost_explorer
                
                # Get spend analysis first
                spend_analysis = await cost_explorer.get_current_spend_analysis()
                safe_print(f"[green]✓ Current spend analysis: ${spend_analysis.get('total_cost', 0):.2f} (last 30 days)[/green]")
                safe_print(f"[dim]Top services analyzed: {len(spend_analysis.get('services', []))}[/dim]")
                
                # Get all Cost Explorer recommendations
                ce_recommendations = await cost_explorer.get_all_recommendations()
                all_recommendations.extend(ce_recommendations)
                
                if ce_recommendations:
                    # Show Cost Explorer summary
                    ce_table = cost_explorer.create_recommendations_summary_table(ce_recommendations)
                    safe_print(ce_table)
                    safe_print()
                    
                    # Show spend analysis table
                    spend_table = cost_explorer.create_spend_analysis_table(spend_analysis)
                    safe_print(spend_table)
                    safe_print()
                else:
                    safe_print("[yellow]No Cost Explorer recommendations found[/yellow]")
                    safe_print("[dim]This may indicate insufficient usage data or well-optimized resources[/dim]")
                    safe_print()
                    
            except Exception as e:
                handle_optimization_error(e, "Cost Explorer")
                safe_print()
        
        # Display combined recommendations
        if all_recommendations:
            safe_print("[bold]Combined Recommendations Summary[/bold]")
            
            table = Table(title="All Cost Optimization Recommendations")
            table.add_column("Source", style="cyan")
            table.add_column("Resource", style="yellow")
            table.add_column("Type", style="green")
            table.add_column("Savings", style="bold green")
            table.add_column("Confidence", style="magenta")
            table.add_column("Description")
            
            total_savings = 0.0
            for rec in all_recommendations:
                table.add_row(
                    rec.source,
                    rec.resource_id[:20] + "..." if len(rec.resource_id) > 20 else rec.resource_id,
                    rec.resource_type,
                    f"${rec.estimated_savings:.2f}",
                    rec.confidence,
                    rec.description[:50] + "..." if len(rec.description) > 50 else rec.description
                )
                total_savings += rec.estimated_savings
            
            safe_print(table)
            safe_print()
            safe_print(f"[bold green]Total Estimated Monthly Savings: ${total_savings:.2f}[/bold green]")
            
            # Export recommendations if requested
            if export:
                saved_files = cost_optimization_core.save_recommendations(
                    all_recommendations, "optimization-recommendations"
                )
                safe_print()
                safe_print("[dim]Recommendations exported to:[/dim]")
                for format, filepath in saved_files.items():
                    safe_print(f"  {format.upper()}: {filepath}")
        else:
            safe_print("[yellow]No cost optimization recommendations found.[/yellow]")
            safe_print("This may indicate:")
            safe_print("  • Your resources are already optimized")
            safe_print("  • Insufficient data for analysis")
            safe_print("  • Missing required permissions or support plan")
            safe_print("  • Service integrations not yet available")
        
        safe_print()
        safe_print("[dim]Note: Trusted Advisor integration is now active. Additional service integrations coming soon.[/dim]")
    
    asyncio.run(get_recommendations())


@app.command(name="cost-snapshot", help="Generate comprehensive cost analysis and optimization snapshot")
def cost_snapshot(
    days: int = typer.Option(30, "--days", help="Number of days for cost analysis"),
    export: bool = typer.Option(True, "--export/--no-export", help="Export snapshot to files"),
):
    """Generate comprehensive cost analysis snapshot"""
    from .services.cost_optimization import cost_optimization_core
    from .services.cost_explorer import cost_explorer
    from .services import cost as cost_analysis
    
    async def generate_snapshot():
        safe_print()
        safe_print("[bold]AWS Cost Optimization - Comprehensive Snapshot[/bold]")
        safe_print()
        
        # Get account info
        account_info = await cost_optimization_core.get_account_info()
        if account_info.get('account_id') == 'unknown':
            safe_print("[red]Error: AWS credentials not configured[/red]")
            safe_print("Run: aws-super-cli optimization-readiness")
            return
        
        safe_print(f"[dim]Account: {account_info.get('account_id')} | Period: {days} days[/dim]")
        safe_print()
        
        try:
            # Get Cost Explorer spend analysis
            safe_print("[bold]Cost Explorer Analysis[/bold]")
            spend_analysis = await cost_explorer.get_current_spend_analysis(days=days)
            
            if spend_analysis.get('total_cost', 0) > 0:
                spend_table = cost_explorer.create_spend_analysis_table(spend_analysis)
                safe_print(spend_table)
                safe_print()
            else:
                safe_print("[yellow]No cost data available for the specified period[/yellow]")
                safe_print()
            
            # Get billing credits
            safe_print("[bold]Billing Credits Analysis[/bold]")
            credits_data = await cost_explorer.get_billing_credits()
            
            if credits_data.get('total_credits', 0) > 0:
                safe_print(f"[green]✓ Total Credits Available: ${credits_data.get('total_credits', 0):.2f}[/green]")
                
                if credits_data.get('credits'):
                    from rich.table import Table
                    credits_table = Table(title="Available Credits Breakdown")
                    credits_table.add_column("Type", style="cyan")
                    credits_table.add_column("Amount", justify="right", style="green")
                    credits_table.add_column("Description", style="yellow")
                    credits_table.add_column("Expiry", style="red")
                    
                    for credit in credits_data['credits']:
                        credits_table.add_row(
                            credit.get('type', 'Unknown'),
                            f"${credit.get('amount', 0):.2f}",
                            credit.get('description', 'N/A')[:50],
                            credit.get('expiry_date', 'N/A')
                        )
                    
                    safe_print(credits_table)
                safe_print()
            else:
                safe_print("[dim]No billing credits found[/dim]")
                safe_print()
            
            # Get all optimization recommendations
            safe_print("[bold]Optimization Recommendations Summary[/bold]")
            all_recommendations = await cost_explorer.get_all_recommendations()
            
            if all_recommendations:
                recommendations_table = cost_explorer.create_recommendations_summary_table(all_recommendations)
                safe_print(recommendations_table)
                safe_print()
                
                total_savings = sum(rec.estimated_savings for rec in all_recommendations)
                safe_print(f"[bold green]Total Potential Monthly Savings: ${total_savings:.2f}[/bold green]")
                safe_print()
                
                if export:
                    # Export comprehensive snapshot
                    snapshot_data = {
                        'account_id': account_info.get('account_id'),
                        'analysis_period_days': days,
                        'spend_analysis': spend_analysis,
                        'credits_analysis': credits_data,
                        'recommendations': [rec.__dict__ for rec in all_recommendations],
                        'total_potential_savings': total_savings,
                        'snapshot_date': datetime.now().isoformat()
                    }
                    
                    saved_files = cost_optimization_core.save_data(
                        snapshot_data, "cost-snapshot"
                    )
                    
                    safe_print("[dim]Snapshot exported to:[/dim]")
                    for format, filepath in saved_files.items():
                        safe_print(f"  {format.upper()}: {filepath}")
            else:
                safe_print("[yellow]No optimization recommendations found[/yellow]")
                safe_print("[dim]This may indicate well-optimized resources or insufficient data[/dim]")
            
        except Exception as e:
            safe_print(f"[red]Error generating cost snapshot: {e}[/red]")
            if "debug" in str(e).lower():
                safe_print("[dim]Try running with --debug for more information[/dim]")
    
    asyncio.run(generate_snapshot())


if __name__ == "__main__":
    app() 