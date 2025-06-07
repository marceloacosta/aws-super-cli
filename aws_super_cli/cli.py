"""AWS Super CLI - Main CLI interface"""

import asyncio
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
    no_args_is_help=True,
)
console = Console()

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
        rprint("[yellow]Which AWS service would you like to list?[/yellow]")
        rprint()
        rprint("[bold]Available services:[/bold]")
        rprint("  [green]aws-super-cli ls ec2[/green]                    # List EC2 instances")
        rprint("  [green]aws-super-cli ls s3[/green]                     # List S3 buckets")
        rprint("  [green]aws-super-cli ls vpc[/green]                    # List VPCs")
        rprint("  [green]aws-super-cli ls rds[/green]                    # List RDS databases")
        rprint("  [green]aws-super-cli ls lambda[/green]                 # List Lambda functions")
        rprint("  [green]aws-super-cli ls elb[/green]                    # List load balancers")
        rprint("  [green]aws-super-cli ls iam[/green]                    # List IAM resources")
        rprint()
        rprint("[bold]Quick examples:[/bold]")
        rprint("  [cyan]aws-super-cli ls ec2 --all-accounts[/cyan]       # EC2 across all accounts")
        rprint("  [cyan]aws-super-cli ls rds --engine postgres[/cyan]    # Find PostgreSQL databases")
        rprint("  [cyan]aws-super-cli help[/cyan]                        # Show more examples")
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
        rprint(f"[dim]Interpreting '{service_lower}' as '{service}'[/dim]")
    
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
        
        rprint(f"[red]Unknown service: '{service}'[/red]")
        rprint()
        
        if unique_suggestions:
            rprint("[yellow]Did you mean:[/yellow]")
            for suggestion in unique_suggestions[:3]:  # Show max 3 suggestions
                rprint(f"  [cyan]aws-super-cli ls {suggestion}[/cyan]")
            rprint()
        
        rprint("[bold]Supported services:[/bold]")
        for svc in SUPPORTED_SERVICES:
            rprint(f"  [green]aws-super-cli ls {svc}[/green]")
        
        rprint()
        rprint("[bold]Quick examples:[/bold]")
        rprint("  [cyan]aws-super-cli ls ec2[/cyan]                    # List EC2 instances")
        rprint("  [cyan]aws-super-cli ls s3[/cyan]                     # List S3 buckets")  
        rprint("  [cyan]aws-super-cli ls rds --engine postgres[/cyan]  # Find PostgreSQL databases")
        rprint("  [cyan]aws-super-cli help[/cyan]                      # Show more examples")
        return
    
    # Multi-account support check
    multi_account_services = ['ec2']  # Services that support multi-account
    
    if all_accounts and service not in multi_account_services:
        rprint(f"[yellow]Multi-account support for {service} coming soon![/yellow]")
        rprint(f"[dim]Running single-account query for {service}...[/dim]")
        rprint()
        all_accounts = False
    elif accounts and service not in multi_account_services:
        rprint(f"[yellow]Multi-account support for {service} coming soon![/yellow]")
        rprint(f"[dim]Running single-account query for {service}...[/dim]")
        rprint()
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
                    console.print(table)
                else:
                    console.print("[yellow]No IAM resources found matching your criteria[/yellow]")
            
            asyncio.run(run_iam_listing())
        else:
            # This shouldn't happen now due to validation above, but keep as fallback
            rprint(f"Multi-account support for {service} coming soon!")
            rprint(f"Multi-account support currently available for: {', '.join(multi_account_services)}")
            rprint(f"Single-account support available for: {', '.join([s for s in SUPPORTED_SERVICES if s not in multi_account_services])}")
            rprint()
            rprint("Examples:")
            rprint("  aws-super-cli ls ec2 --all-accounts        # Multi-account EC2 (works now!)")
            rprint("  aws-super-cli ls s3                        # Single-account S3")
            rprint("  aws-super-cli ls rds --engine postgres     # Single-account RDS")
            rprint("  aws-super-cli accounts                     # List available profiles")
    
    except Exception as e:
        with console.status("[bold red]Error occurred...", spinner="dots"):
            pass
        
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        
        # Provide helpful suggestions based on the error
        error_str = str(e).lower()
        if "credentials" in error_str or "access denied" in error_str:
            console.print()
            console.print("[yellow]Credential issues detected. Try:[/yellow]")
            console.print("  [cyan]aws-super-cli version[/cyan]           # Check credential status")
            console.print("  [cyan]aws configure[/cyan]                  # Configure credentials")
            console.print("  [cyan]aws sts get-caller-identity[/cyan]    # Test AWS access")
        elif "region" in error_str:
            console.print()
            console.print("[yellow]Region issues detected. Try:[/yellow]")
            console.print(f"  [cyan]aws-super-cli ls {service} --region us-east-1[/cyan]  # Specify region")
            console.print("  [cyan]aws configure set region us-east-1[/cyan]           # Set default region")
        
        # Always show debug info for now since we're in development
        console.print()
        console.print("[bold red]Debug info:[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


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
        rprint("[yellow]Which cost analysis would you like?[/yellow]")
        rprint()
        rprint("[bold]Most Popular:[/bold]")
        rprint("  [cyan]aws-super-cli cost summary[/cyan]              # Overall cost overview")
        rprint("  [cyan]aws-super-cli cost top-spend[/cyan]            # Biggest spending services")
        rprint("  [cyan]aws-super-cli cost credits[/cyan]              # Credit usage analysis")
        rprint()
        rprint("[bold]All Available Commands:[/bold]")
        rprint("  [green]summary[/green]              # Comprehensive cost summary")
        rprint("  [green]top-spend[/green]            # Top spending services (gross costs)")
        rprint("  [green]with-credits[/green]         # Top spending services (net costs)")
        rprint("  [green]by-account[/green]           # Costs broken down by account")
        rprint("  [green]daily[/green]                # Daily cost trends")
        rprint("  [green]month[/green]                # Current month costs")
        rprint("  [green]credits[/green]              # Credit usage trends")
        rprint("  [green]credits-by-service[/green]   # Credit usage by service")
        rprint()
        rprint("[bold]Quick start:[/bold]")
        rprint("  [cyan]aws-super-cli cost summary[/cyan]              # Start here!")
        return
    
    command_lower = command.lower()
    
    try:
        if command_lower == "top-spend":
            console.print(f"[cyan]Analyzing top spending services for the last {days} days...[/cyan]")
            
            # Pass debug flag
            services_cost = asyncio.run(cost_analysis.get_cost_by_service(days=days, limit=limit, debug=debug))
            if not services_cost:
                console.print("[yellow]No cost data available. Check permissions and try again.[/yellow]")
                return
            
            # Check for low cost data and show guidance
            is_low_cost = cost_analysis.check_low_cost_data(services_cost, console)
            
            table = cost_analysis.create_cost_table(
                services_cost, 
                f"Top {len(services_cost)} AWS Services by Cost (Last {days} days) - Gross Costs"
            )
            console.print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in services_cost)
            console.print(f"\n[green]Total gross cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
            # Also show with credits applied for comparison
            console.print(f"\n[dim]Use '--include-credits' flag to see costs with credits applied[/dim]")
            
        elif command_lower == "with-credits":
            console.print(f"[cyan]Analyzing top spending services (WITH credits applied) for the last {days} days...[/cyan]")
            
            services_cost = asyncio.run(cost_analysis.get_cost_by_service(days=days, limit=limit, debug=debug, include_credits=True))
            if not services_cost:
                console.print("[yellow]No cost data available. Check permissions and try again.[/yellow]")
                return
            
            table = cost_analysis.create_cost_table(
                services_cost, 
                f"Top {len(services_cost)} AWS Services by Cost (Last {days} days) - Net Costs (With Credits)"
            )
            console.print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in services_cost)
            console.print(f"\n[green]Total net cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
        elif command_lower == "by-account":
            console.print(f"[cyan]Analyzing costs by account for the last {days} days...[/cyan]")
            
            accounts_cost = asyncio.run(cost_analysis.get_cost_by_account(days=days, debug=debug))
            if not accounts_cost:
                console.print("[yellow]No account cost data available.[/yellow]")
                return
            
            # Check for low cost data
            cost_analysis.check_low_cost_data(accounts_cost, console)
            
            table = cost_analysis.create_cost_table(
                accounts_cost[:limit], 
                f"AWS Costs by Account (Last {days} days) - Gross Costs"
            )
            console.print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in accounts_cost[:limit])
            console.print(f"\n[green]Total gross cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
        elif command_lower == "daily":
            console.print("[cyan]Analyzing daily cost trends...[/cyan]")
            
            daily_costs = asyncio.run(cost_analysis.get_daily_costs(days=days, debug=debug))
            if not daily_costs:
                console.print("[yellow]No daily cost data available.[/yellow]")
                return
            
            # Check for low cost data
            cost_analysis.check_low_cost_data(daily_costs, console)
            
            table = cost_analysis.create_cost_table(
                daily_costs, 
                "Daily Cost Trend (Last 7 days) - Gross Costs"
            )
            console.print(table)
            
            if len(daily_costs) >= 2:
                yesterday_cost = daily_costs[-1]['Raw_Cost']
                day_before_cost = daily_costs[-2]['Raw_Cost']
                change = yesterday_cost - day_before_cost
                if change > 0:
                    console.print(f"[yellow]Daily cost increased by {cost_analysis.format_cost_amount(str(change))}[/yellow]")
                elif change < 0:
                    console.print(f"[green]Daily cost decreased by {cost_analysis.format_cost_amount(str(abs(change)))}[/green]")
                else:
                    console.print("[blue]Daily cost remained stable[/blue]")
                    
        elif command_lower == "summary":
            console.print(f"[cyan]Getting cost summary for the last {days} days...[/cyan]")
            
            summary = asyncio.run(cost_analysis.get_cost_summary(days=days, debug=debug))
            
            console.print("\n[bold]Cost Summary[/bold]")
            console.print(f"Period: {summary['period']}")
            console.print(f"Gross Cost (without credits): [green]{summary['gross_cost']}[/green]")
            console.print(f"Net Cost (with credits):      [blue]{summary['net_cost']}[/blue]")
            console.print(f"Credits Applied:              [yellow]{summary['credits_applied']}[/yellow]")
            console.print(f"Daily Average (gross):        [cyan]{summary['daily_avg_gross']}[/cyan]")
            console.print(f"Daily Average (net):          [dim]{summary['daily_avg_net']}[/dim]")
            console.print(f"Trend: {summary['trend']}")
            
        elif command_lower == "month":
            console.print("[cyan]Getting current month costs (matches AWS console)...[/cyan]")
            
            month_data = asyncio.run(cost_analysis.get_current_month_costs(debug=debug))
            
            console.print("\n[bold]Current Month Costs[/bold]")
            console.print(f"Period: {month_data['period']}")
            console.print(f"Gross Cost (without credits): [green]{month_data['gross_cost']}[/green]")
            console.print(f"Net Cost (with credits):      [blue]{month_data['net_cost']}[/blue]")
            console.print(f"Credits Applied:              [yellow]{month_data['credits_applied']}[/yellow]")
            
        elif command_lower == "credits":
            console.print("[cyan]Analyzing AWS credits usage patterns...[/cyan]")
            
            credit_analysis = asyncio.run(cost_analysis.get_credit_analysis(days=90, debug=debug))
            
            if 'error' in credit_analysis:
                console.print(f"[red]Error: {credit_analysis['error']}[/red]")
                console.print(f"[yellow]{credit_analysis['note']}[/yellow]")
                return
            
            # Show credit analysis table
            table = cost_analysis.create_credit_analysis_table(credit_analysis)
            console.print(table)
            
            # Show monthly trend
            console.print("\n[bold]Monthly Credit Usage Trend[/bold]")
            for month_data in credit_analysis['credit_usage_trend']:
                credits = cost_analysis.format_cost_amount(str(month_data['credits_used']))
                gross = cost_analysis.format_cost_amount(str(month_data['gross_cost']))
                console.print(f"  {month_data['month']}: [yellow]{credits}[/yellow] credits applied (gross: [dim]{gross}[/dim])")
            
            # Important note about remaining balance
            console.print(f"\n[bold yellow]Important:[/bold yellow]")
            console.print(f"[dim]{credit_analysis['note']}[/dim]")
            console.print(f"[cyan]To see remaining credit balance, visit:[/cyan]")
            console.print(f"   [link]https://console.aws.amazon.com/billing/home#/credits[/link]")
            
        elif command_lower == "credits-by-service":
            console.print(f"[cyan]Analyzing credit usage by service (last {days} days)...[/cyan]")
            
            credit_usage = asyncio.run(cost_analysis.get_credit_usage_by_service(days=days, debug=debug))
            
            if not credit_usage:
                console.print("[yellow]No services found with significant credit usage.[/yellow]")
                return
            
            # Show credit usage by service
            table = cost_analysis.create_credit_usage_table(
                credit_usage[:limit], 
                f"Top {min(len(credit_usage), limit)} Services by Credit Usage (Last {days} days)"
            )
            console.print(table)
            
            # Summary
            total_credits_used = sum(item['Raw_Credits'] for item in credit_usage)
            console.print(f"\n[green]Total credits applied across {len(credit_usage)} services: {cost_analysis.format_cost_amount(str(total_credits_used))}[/green]")
            
            # Show highest coverage services
            high_coverage = [s for s in credit_usage if float(s['Credit_Coverage'].replace('%', '')) > 90]
            if high_coverage:
                console.print(f"\n[cyan]Services with >90% credit coverage:[/cyan]")
                for service in high_coverage[:3]:
                    console.print(f"  • {service['Service']}: {service['Credit_Coverage']} coverage")
            
        else:
            console.print(f"[red]Unknown cost command: {command}[/red]")
            console.print("\n[bold]Available commands:[/bold]")
            console.print("  aws-super-cli cost top-spend          # Show top spending services (gross costs)")
            console.print("  aws-super-cli cost with-credits       # Show top spending services (net costs)")
            console.print("  aws-super-cli cost by-account         # Show costs by account")
            console.print("  aws-super-cli cost daily              # Show daily cost trends")
            console.print("  aws-super-cli cost summary            # Show comprehensive cost summary")
            console.print("  aws-super-cli cost month              # Show current month costs")
            console.print("  aws-super-cli cost credits            # Show credit usage analysis and trends")
            console.print("  aws-super-cli cost credits-by-service # Show credit usage breakdown by service")
            console.print("\n[bold]Cost Types:[/bold]")
            console.print("  • [green]Gross costs[/green]: What you'd pay without credits (matches console)")
            console.print("  • [blue]Net costs[/blue]: What you actually pay after credits")
            console.print("  • [yellow]Credits[/yellow]: Amount of credits applied")
            console.print("\n[bold]Credit Analysis:[/bold]")
            console.print("  • [cyan]Usage trends[/cyan]: Historical credit consumption patterns")
            console.print("  • [magenta]Service breakdown[/magenta]: Which services use most credits")
            console.print("  • [yellow]Coverage analysis[/yellow]: Credit coverage percentage by service")
            console.print("\n[bold]Options:[/bold]")
            console.print("  --days 7                 # Analyze last 7 days")
            console.print("  --limit 5                # Show top 5 results")
            console.print("  --debug                  # Show debug information")
            
    except Exception as e:
        console.print(f"[red]Error analyzing costs: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            console.print("")
            for message in help_messages:
                console.print(message)
        console.print("\n[yellow]Note: Cost analysis requires Cost Explorer permissions:[/yellow]")
        console.print("  • ce:GetCostAndUsage")
        console.print("  • ce:GetDimensionValues")
        raise typer.Exit(1)


@app.command()
def version():
    """Show AWS Super CLI version and current AWS context"""
    from . import __version__
    
    rprint(f"[bold cyan]AWS Super CLI[/bold cyan] version {__version__}")
    
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
            
            rprint(f"Credentials working: {credential_source}")
            rprint(f"Account ID: {account_id}")
            rprint(f"Default region: {region}")
            
            # Test basic AWS access
            try:
                session = aws_session.session
                ec2 = session.client('ec2', region_name=region or 'us-east-1')
                
                # Quick test - list instances (this is free)
                response = ec2.describe_instances(MaxResults=5)
                instance_count = sum(len(reservation['Instances']) for reservation in response['Reservations'])
                
                if instance_count > 0:
                    rprint(f"EC2 API access working - found {instance_count} instances in {region or 'us-east-1'}")
                else:
                    rprint(f"EC2 API access working - no instances in {region or 'us-east-1'}")
                    
            except Exception as e:
                rprint(f"EC2 API error: {e}")
                help_messages = aws_session.get_credential_help(e)
                if help_messages:
                    rprint("")
                    for message in help_messages:
                        rprint(message)
                
        else:
            rprint(f"[red]❌ No valid AWS credentials found[/red]")
            if error:
                rprint(f"[red]Error: {error}[/red]")
                
            rprint("\n[yellow]Setup AWS credentials using one of:[/yellow]")
            rprint("  • aws configure")
            rprint("  • AWS SSO: aws sso login --profile <profile>")
            rprint("  • Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            rprint("  • IAM roles or EC2 instance profiles")
            
    except Exception as e:
        rprint(f"[red]Error checking credentials: {e}[/red]")


@app.command()
def test():
    """Test AWS connectivity and credentials"""
    rprint("[bold cyan]Testing AWS connectivity...[/bold cyan]")
    
    try:
        # Test credential detection
        has_creds, account_id, error = aws_session.check_credentials()
        
        if has_creds and account_id:
            credential_source = aws_session.detect_credential_source()
            rprint(f"Credentials working: {credential_source}")
            rprint(f"Account ID: {account_id}")
            
            # Test region detection
            import boto3
            session = boto3.Session()
            region = session.region_name or 'us-east-1'
            rprint(f"Default region: {region}")
            
            # Test EC2 permissions
            rprint("\nTesting EC2 permissions...")
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
                    rprint(f"EC2 API access working - found {instance_count} instances in {region}")
                else:
                    rprint(f"EC2 API access working - no instances in {region}")
                    
            except Exception as e:
                rprint(f"[yellow]API access test failed: {e}[/yellow]")
            
        elif has_creds and error:
            rprint(f"Credentials found but invalid: {error}")
            help_messages = aws_session.get_credential_help(error)
            if help_messages:
                rprint("")
                for message in help_messages:
                    rprint(message)
        else:
            rprint("No AWS credentials found")
            help_messages = aws_session.get_credential_help(Exception("NoCredentialsError"))
            for message in help_messages:
                rprint(message)
                
    except Exception as e:
        rprint(f"Unexpected error: {e}")


@app.command()
def accounts(
    health_check: bool = typer.Option(True, "--health-check/--no-health-check", help="Perform health checks on accounts"),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by account category"),
    show_details: bool = typer.Option(False, "--details", help="Show detailed account information")
):
    """List available AWS accounts with intelligent categorization and health checks"""
    console.print("[bold cyan]AWS Account Intelligence[/bold cyan]")
    console.print()
    
    try:
        if health_check:
            console.print("[dim]Discovering accounts and performing health checks...[/dim]")
        else:
            console.print("[dim]Discovering accounts (skipping health checks for speed)...[/dim]")
        
        # Get enhanced account information
        async def get_accounts():
            return await account_intelligence.get_enhanced_accounts(include_health_check=health_check)
        
        enhanced_accounts = asyncio.run(get_accounts())
        
        if not enhanced_accounts:
            console.print("[yellow]No AWS accounts found.[/yellow]")
            console.print("\n[dim]Set up profiles with:[/dim]")
            console.print("  aws configure --profile mycompany")
            console.print("  aws configure sso")
            return
        
        # Filter by category if specified
        if category:
            try:
                filter_category = AccountCategory(category.lower())
                enhanced_accounts = [acc for acc in enhanced_accounts if acc.category == filter_category]
                
                if not enhanced_accounts:
                    console.print(f"[yellow]No accounts found in category '{category}'[/yellow]")
                    return
            except ValueError:
                console.print(f"[red]Invalid category '{category}'. Valid categories: {', '.join([c.value for c in AccountCategory])}[/red]")
                return
        
        # Create and display enhanced table
        table = account_intelligence.create_enhanced_accounts_table(enhanced_accounts)
        console.print(table)
        
        # Summary statistics
        total_accounts = len(enhanced_accounts)
        healthy_accounts = len([acc for acc in enhanced_accounts if acc.health.value == 'healthy'])
        
        # Group by category for summary
        categorized = account_intelligence.get_accounts_by_category(enhanced_accounts)
        
        console.print(f"\n[bold]Account Summary[/bold]")
        console.print(f"Total Accounts: {total_accounts}")
        if health_check:
            console.print(f"Healthy Accounts: [green]{healthy_accounts}[/green] / {total_accounts}")
        
        if len(categorized) > 1:
            console.print("\n[bold]Categories:[/bold]")
            for cat, accounts in categorized.items():
                if cat == AccountCategory.PRODUCTION:
                    console.print(f"  [red bold]{cat.value}[/red bold]: {len(accounts)} accounts")
                elif cat == AccountCategory.STAGING:
                    console.print(f"  [yellow]{cat.value}[/yellow]: {len(accounts)} accounts")
                elif cat == AccountCategory.DEVELOPMENT:
                    console.print(f"  [green]{cat.value}[/green]: {len(accounts)} accounts")
                else:
                    console.print(f"  {cat.value}: {len(accounts)} accounts")
        
        # Enhanced usage examples
        console.print("\n[bold]Multi-Account Operations:[/bold]")
        console.print("  [cyan]aws-super-cli accounts --category production[/cyan]      # View production accounts only")
        console.print("  [cyan]aws-super-cli accounts --no-health-check[/cyan]         # Fast account listing")
        console.print("  [cyan]aws-super-cli accounts nickname[/cyan]                  # Manage account nicknames")
        console.print()
        console.print("  [cyan]aws-super-cli ls ec2 --all-accounts[/cyan]              # Query all accessible accounts")
        console.print("  [cyan]aws-super-cli audit --all-accounts[/cyan]               # Security audit across accounts")
        console.print("  [cyan]aws-super-cli ls s3 --accounts prod-*[/cyan]           # Query accounts by pattern")
        
        # Show example with actual profile names
        if len(enhanced_accounts) >= 2:
            example_profiles = [acc.name for acc in enhanced_accounts[:2]]
            console.print(f"  [cyan]aws-super-cli ls vpc --accounts {','.join(example_profiles)}[/cyan] # Query specific accounts")
        
        # Health warnings
        if health_check:
            unhealthy_accounts = [acc for acc in enhanced_accounts if acc.health.value in ['warning', 'error']]
            if unhealthy_accounts:
                console.print(f"\n[yellow]Health Issues Found[/yellow]")
                console.print(f"Run [cyan]aws-super-cli accounts health[/cyan] for detailed health information")
        
    except Exception as e:
        console.print(f"[red]Error discovering accounts: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            console.print("")
            for message in help_messages:
                console.print(message)


@app.command(name="accounts-health", help="Detailed health information for AWS accounts")
def accounts_health():
    """Show detailed health information for AWS accounts"""
    console.print("[bold cyan]AWS Account Health Report[/bold cyan]")
    console.print()
    
    try:
        console.print("[dim]Performing comprehensive health checks...[/dim]")
        
        async def get_health_report():
            accounts = await account_intelligence.get_enhanced_accounts(include_health_check=True)
            return accounts
        
        accounts = asyncio.run(get_health_report())
        
        if not accounts:
            console.print("[yellow]No accounts found[/yellow]")
            return
        
        # Group by health status
        healthy = [acc for acc in accounts if acc.health.value == 'healthy']
        warning = [acc for acc in accounts if acc.health.value == 'warning']
        error = [acc for acc in accounts if acc.health.value == 'error']
        unknown = [acc for acc in accounts if acc.health.value == 'unknown']
        
        # Health summary
        console.print(f"[bold]Health Summary:[/bold]")
        console.print(f"  [green]Healthy: {len(healthy)}[/green]")
        console.print(f"  [yellow]Warning: {len(warning)}[/yellow]")
        console.print(f"  [red]Error: {len(error)}[/red]")
        console.print(f"  [dim]Unknown: {len(unknown)}[/dim]")
        console.print()
        
        # Show problematic accounts first
        if error:
            console.print("[red bold]Accounts with Errors:[/red bold]")
            for account in error:
                console.print(f"  [red]✗ {account.name}[/red] ({account.account_id})")
                console.print(f"    Category: {account.category.value}")
            console.print()
        
        if warning:
            console.print("[yellow bold]Accounts with Warnings:[/yellow bold]")
            for account in warning:
                console.print(f"  [yellow]⚠ {account.name}[/yellow] ({account.account_id})")
                console.print(f"    Category: {account.category.value}")
            console.print()
        
        if healthy:
            console.print("[green bold]Healthy Accounts:[/green bold]")
            for account in healthy:
                console.print(f"  [green]✓ {account.name}[/green] ({account.account_id}) - {account.category.value}")
        
        # Recommendations
        console.print("\n[bold]Recommendations:[/bold]")
        if error:
            console.print("  [red]• Fix authentication issues for error accounts[/red]")
        if warning:
            console.print("  [yellow]• Review permission configurations for warning accounts[/yellow]")
        if len(healthy) == len(accounts):
            console.print("  [green]• All accounts are healthy![/green]")
        
    except Exception as e:
        console.print(f"[red]Error generating health report: {e}[/red]")


@app.command(name="accounts-nickname", help="Manage account nicknames")
def accounts_nickname(
    profile: Optional[str] = typer.Argument(None, help="Profile name to set nickname for"),
    nickname: Optional[str] = typer.Argument(None, help="Nickname to set")
):
    """Manage account nicknames for easier identification"""
    
    if not profile:
        # Show current nicknames
        console.print("[bold cyan]Account Nicknames[/bold cyan]")
        console.print()
        
        nicknames = account_intelligence.load_nicknames()
        
        if not nicknames:
            console.print("[yellow]No nicknames set[/yellow]")
            console.print("\n[dim]Set a nickname with:[/dim]")
            console.print("  aws-super-cli accounts-nickname myprofile \"My Company Prod\"")
            return
        
        # Show nicknames table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Profile", style="cyan", min_width=15)
        table.add_column("Nickname", style="green", min_width=20)
        
        for profile_name, nick in nicknames.items():
            table.add_row(profile_name, nick)
        
        console.print(table)
        console.print(f"\n[green]Found {len(nicknames)} nicknames[/green]")
        return
    
    if not nickname:
        console.print(f"[red]Please provide a nickname for profile '{profile}'[/red]")
        console.print(f"[dim]Example: aws-super-cli accounts-nickname {profile} \"My Company Production\"[/dim]")
        return
    
    # Set nickname
    try:
        account_intelligence.save_nickname(profile, nickname)
        console.print(f"[green]Set nickname for '{profile}': [bold]{nickname}[/bold][/green]")
        console.print(f"\n[dim]Run 'aws-super-cli accounts' to see the updated display[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error setting nickname: {e}[/red]")


@app.command(name="accounts-dashboard", help="Show comprehensive account dashboard")
def accounts_dashboard():
    """Show comprehensive multi-account dashboard"""
    console.print("[bold cyan]AWS Multi-Account Dashboard[/bold cyan]")
    console.print()
    
    try:
        console.print("[dim]Loading account intelligence...[/dim]")
        
        async def get_dashboard_data():
            return await account_intelligence.get_enhanced_accounts(include_health_check=True)
        
        accounts = asyncio.run(get_dashboard_data())
        
        if not accounts:
            console.print("[yellow]No accounts found[/yellow]")
            return
        
        # Overall statistics
        total = len(accounts)
        healthy = len([acc for acc in accounts if acc.health.value == 'healthy'])
        
        console.print(f"[bold]Account Overview[/bold]")
        console.print(f"Total Accounts: {total}")
        console.print(f"Health Score: [{'green' if healthy/total > 0.8 else 'yellow' if healthy/total > 0.5 else 'red'}]{healthy}/{total} ({healthy/total*100:.1f}%)[/]")
        console.print()
        
        # Category breakdown
        categorized = account_intelligence.get_accounts_by_category(accounts)
        
        console.print("[bold]Account Categories[/bold]")
        category_table = Table(show_header=True, header_style="bold magenta")
        category_table.add_column("Category", style="cyan", min_width=15)
        category_table.add_column("Count", style="green", min_width=8)
        category_table.add_column("Health", style="yellow", min_width=12)
        category_table.add_column("Accounts", min_width=30)
        
        for category, cat_accounts in categorized.items():
            healthy_count = len([acc for acc in cat_accounts if acc.health.value == 'healthy'])
            account_names = ', '.join([acc.name for acc in cat_accounts[:3]])
            if len(cat_accounts) > 3:
                account_names += f" (+{len(cat_accounts)-3} more)"
            
            health_display = f"{healthy_count}/{len(cat_accounts)}"
            if healthy_count == len(cat_accounts):
                health_display = f"[green]{health_display}[/green]"
            elif healthy_count == 0:
                health_display = f"[red]{health_display}[/red]"
            else:
                health_display = f"[yellow]{health_display}[/yellow]"
            
            category_display = category.value
            if category == AccountCategory.PRODUCTION:
                category_display = f"[red bold]{category_display}[/red bold]"
            elif category == AccountCategory.STAGING:
                category_display = f"[yellow]{category_display}[/yellow]"
            elif category == AccountCategory.DEVELOPMENT:
                category_display = f"[green]{category_display}[/green]"
            
            category_table.add_row(
                category_display,
                str(len(cat_accounts)),
                health_display,
                account_names
            )
        
        console.print(category_table)
        
        # Quick actions
        console.print(f"\n[bold]Quick Actions[/bold]")
        console.print(f"  [cyan]aws-super-cli accounts --category production[/cyan]      # Focus on production")
        console.print(f"  [cyan]aws-super-cli audit --all-accounts --summary[/cyan]     # Security overview")
        console.print(f"  [cyan]aws-super-cli cost by-account[/cyan]                    # Cost breakdown")
        console.print(f"  [cyan]aws-super-cli accounts-health[/cyan]                    # Detailed health report")
        
        # Warnings and recommendations
        unhealthy = [acc for acc in accounts if acc.health.value in ['warning', 'error']]
        if unhealthy:
            console.print(f"\n[yellow]{len(unhealthy)} accounts need attention[/yellow]")
            console.print(f"Run [cyan]aws-super-cli accounts-health[/cyan] for details")
        
        # Production account highlighting
        prod_accounts = categorized.get(AccountCategory.PRODUCTION, [])
        if prod_accounts:
            unhealthy_prod = [acc for acc in prod_accounts if acc.health.value in ['warning', 'error']]
            if unhealthy_prod:
                console.print(f"\n[red bold]CRITICAL: {len(unhealthy_prod)} production accounts have health issues![/red bold]")
            else:
                console.print(f"\n[green]All {len(prod_accounts)} production accounts are healthy[/green]")
        
    except Exception as e:
        console.print(f"[red]Error generating dashboard: {e}[/red]")


@app.command()
def audit(
    services: Optional[str] = typer.Option("s3,iam,network,compute", "--services", help="Comma-separated services to audit (s3, iam, network, compute)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Specific region to query"),
    all_regions: bool = typer.Option(True, "--all-regions/--no-all-regions", help="Query all regions (default) or current region only"),
    all_accounts: bool = typer.Option(False, "--all-accounts", help="Query all accessible AWS accounts"),
    accounts: Optional[str] = typer.Option(None, "--accounts", help="Comma-separated profiles or pattern (e.g., 'prod-*,staging')"),
    summary_only: bool = typer.Option(False, "--summary", help="Show only summary statistics"),
    export_format: Optional[str] = typer.Option(None, "--export", help="Export format: csv, txt, html"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: auto-generated)"),
):
    """Run security audit to identify misconfigurations"""
    
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
                console.print("[yellow]No accessible AWS accounts found.[/yellow]")
                console.print("\n[dim]Run 'aws-super-cli accounts' to see available profiles[/dim]")
                return
                
            console.print(f"[dim]Auditing {len(profiles_to_query)} accounts: {', '.join(profiles_to_query)}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error discovering accounts: {e}[/red]")
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
            console.print(f"[yellow]No profiles found matching: {accounts}[/yellow]")
            console.print("\n[dim]Run 'aws-super-cli accounts' to see available profiles[/dim]")
            return
            
        console.print(f"[dim]Auditing accounts: {', '.join(profiles_to_query)}[/dim]")
    else:
        # Single account (current profile)
        profiles_to_query = None  # Will use current profile by default
        console.print("[dim]Auditing current account...[/dim]")
    
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
            console.print(f"\n[bold]Security Audit Summary[/bold]")
            console.print(f"Security Score: [{'red' if summary['score'] < 70 else 'yellow' if summary['score'] < 90 else 'green'}]{summary['score']}/100[/]")
            console.print(f"Total Findings: {summary['total']}")
            
            if summary['total'] > 0:
                console.print(f"  High Risk: [red]{summary['high']}[/red]")
                console.print(f"  Medium Risk: [yellow]{summary['medium']}[/yellow]")
                console.print(f"  Low Risk: [green]{summary['low']}[/green]")
                
                # Show breakdown by service
                console.print(f"\nFindings by Service:")
                for service, count in summary['services'].items():
                    console.print(f"  {service}: {count}")
            else:
                console.print("[green]No security issues found[/green]")
            
            return
        
        # Show detailed findings
        show_account = profiles_to_query is not None and len(profiles_to_query) > 1
        
        # Handle export options
        if export_format:
            # Validate export format
            if export_format.lower() not in ['csv', 'txt', 'html']:
                console.print(f"[red]Error: Unsupported export format '{export_format}'. Supported formats: csv, txt, html[/red]")
                return
            
            # Generate output filename if not provided
            if not output_file:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"aws_security_audit_{timestamp}.{export_format.lower()}"
            
            # Ensure the filename has the correct extension
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
                
                console.print(f"[green]Audit results exported to: {output_file}[/green]")
                
                # Show summary in terminal as well
                console.print(f"\n[bold]Security Summary[/bold]")
                console.print(f"Security Score: [{'red' if summary['score'] < 70 else 'yellow' if summary['score'] < 90 else 'green'}]{summary['score']}/100[/]")
                console.print(f"Found {summary['total']} security findings:")
                console.print(f"  [red]High Risk: {summary['high']}[/red]")
                console.print(f"  [yellow]Medium Risk: {summary['medium']}[/yellow]")
                console.print(f"  [green]Low Risk: {summary['low']}[/green]")
                
                return
                
            except Exception as export_error:
                console.print(f"[red]Error exporting results: {export_error}[/red]")
                # Continue with normal output if export fails
        
        table = audit_service.create_audit_table(findings, show_account=show_account)
        console.print(table)
        
        # Show summary at the end
        console.print(f"\n[bold]Security Summary[/bold]")
        console.print(f"Security Score: [{'red' if summary['score'] < 70 else 'yellow' if summary['score'] < 90 else 'green'}]{summary['score']}/100[/]")
        console.print(f"Found {summary['total']} security findings:")
        console.print(f"  [red]High Risk: {summary['high']}[/red]")
        console.print(f"  [yellow]Medium Risk: {summary['medium']}[/yellow]")
        console.print(f"  [green]Low Risk: {summary['low']}[/green]")
        
        # Recommendations
        if summary['high'] > 0:
            console.print(f"\n[red]PRIORITY: Address {summary['high']} high-risk findings immediately[/red]")
        elif summary['medium'] > 0:
            console.print(f"\n[yellow]RECOMMENDED: Review {summary['medium']} medium-risk findings[/yellow]")
        else:
            console.print(f"\n[green]Account security looks good! Consider reviewing {summary['low']} low-risk items[/green]")
            
        if profiles_to_query:
            account_count = len(profiles_to_query)
            console.print(f"\n[dim]Audit completed across {account_count} accounts[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error running security audit: {e}[/red]")
        if "--debug" in str(e):
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


@app.command(name="help", help="Show help information and common examples")
def help_command():
    """Show help information"""
    rprint()
    rprint("[bold]AWS Super CLI - Quick Reference[/bold]")
    rprint()
    rprint("[bold]Most Common Commands:[/bold]")
    rprint("  [cyan]aws-super-cli ls ec2[/cyan]                    # List EC2 instances")
    rprint("  [cyan]aws-super-cli ls s3[/cyan]                     # List S3 buckets") 
    rprint("  [cyan]aws-super-cli audit[/cyan]                     # Run security audit")
    rprint("  [cyan]aws-super-cli accounts[/cyan]                  # Show available accounts")
    rprint("  [cyan]aws-super-cli cost summary[/cyan]              # Cost overview")
    rprint()
    rprint("[bold]Resource Discovery:[/bold]")
    rprint("  [cyan]aws-super-cli ls ec2 --all-accounts[/cyan]     # EC2 across all accounts")
    rprint("  [cyan]aws-super-cli ls rds --engine postgres[/cyan]  # Find PostgreSQL databases")
    rprint("  [cyan]aws-super-cli ls lambda --runtime python[/cyan] # Find Python functions")
    rprint()
    rprint("[bold]Security Auditing:[/bold]")
    rprint("  [cyan]aws-super-cli audit --summary[/cyan]           # Quick security overview")
    rprint("  [cyan]aws-super-cli audit --all-accounts[/cyan]      # Audit all accounts")
    rprint("  [cyan]aws-super-cli audit --services network[/cyan]  # Network security only")
    rprint("  [cyan]aws-super-cli audit --services s3,iam[/cyan]   # S3 and IAM audit only")
    rprint("  [cyan]aws-super-cli audit --export csv[/cyan]        # Export results to CSV")
    rprint("  [cyan]aws-super-cli audit --export html[/cyan]       # Export results to HTML")
    rprint("  [cyan]aws-super-cli audit --export txt -o report.txt[/cyan] # Export to specific file")
    rprint()
    rprint("[bold]ARN Intelligence:[/bold]")
    rprint("  [cyan]aws-super-cli explain arn:aws:iam::123:user/john[/cyan] # Explain an ARN")
    rprint("  [cyan]aws-super-cli ls iam --show-full-arns[/cyan]    # Show full ARNs")
    rprint("  [cyan]aws-super-cli ls iam[/cyan]                     # Smart ARN display (default)")
    rprint()
    rprint("[bold]Cost Analysis:[/bold]")
    rprint("  [cyan]aws-super-cli cost summary[/cyan]              # Overall cost trends")
    rprint("  [cyan]aws-super-cli cost top-spend[/cyan]            # Biggest cost services")
    rprint("  [cyan]aws-super-cli cost credits[/cyan]              # Credit usage analysis")
    rprint()
    rprint("[bold]Multi-Account Intelligence:[/bold]")
    rprint("  [cyan]aws-super-cli accounts[/cyan]                   # Smart account categorization & health")
    rprint("  [cyan]aws-super-cli accounts --category production[/cyan] # Filter by category") 
    rprint("  [cyan]aws-super-cli accounts-dashboard[/cyan]         # Comprehensive account overview")
    rprint("  [cyan]aws-super-cli accounts-health[/cyan]            # Detailed health report")
    rprint("  [cyan]aws-super-cli accounts-nickname myprofile \"Name\"[/cyan] # Set account nicknames")
    rprint()
    rprint("[bold]For detailed help:[/bold]")
    rprint("  [cyan]aws-super-cli --help[/cyan]                    # Full command reference")
    rprint("  [cyan]aws-super-cli ls --help[/cyan]                 # Resource listing help")
    rprint("  [cyan]aws-super-cli audit --help[/cyan]              # Security audit help")
    rprint("  [cyan]aws-super-cli cost --help[/cyan]               # Cost analysis help")
    rprint()


@app.command(name="explain", help="Explain AWS ARNs and break them down into components")
def explain_arn(
    arn: str = typer.Argument(..., help="ARN to explain (e.g., arn:aws:iam::123456789012:user/john)")
):
    """Explain an AWS ARN and break it down into components"""
    
    if not arn.startswith('arn:'):
        rprint(f"[red]Error: '{arn}' does not appear to be a valid ARN[/red]")
        rprint()
        rprint("[bold]ARN format:[/bold]")
        rprint("  arn:partition:service:region:account:resource")
        rprint()
        rprint("[bold]Examples:[/bold]")
        rprint("  [cyan]aws-super-cli explain arn:aws:iam::123456789012:user/john[/cyan]")
        rprint("  [cyan]aws-super-cli explain arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0[/cyan]")
        rprint("  [cyan]aws-super-cli explain arn:aws:s3:::my-bucket[/cyan]")
        return
    
    # Parse and explain the ARN
    explanation = arn_intelligence.explain_arn(arn)
    
    if "error" in explanation:
        rprint(f"[red]Error: {explanation['error']}[/red]")
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
    
    rprint()
    console.print(table)
    rprint()
    
    # Show the human-readable version
    human_name = arn_intelligence.get_human_readable_name(arn)
    rprint(f"[bold]Human-readable name:[/bold] [green]{human_name}[/green]")
    
    # Show smart truncated versions
    rprint()
    rprint("[bold]Display options:[/bold]")
    rprint(f"  Short (20 chars): [yellow]{arn_intelligence.smart_truncate(arn, 20)}[/yellow]")
    rprint(f"  Medium (30 chars): [yellow]{arn_intelligence.smart_truncate(arn, 30)}[/yellow]")
    rprint(f"  Long (50 chars): [yellow]{arn_intelligence.smart_truncate(arn, 50)}[/yellow]")
    rprint()


if __name__ == "__main__":
    app() 