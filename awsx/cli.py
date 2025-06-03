"""AWS Super CLI - Main CLI interface"""

import asyncio
from typing import List, Optional
import typer
from rich.console import Console
from rich import print as rprint

from .services import ec2, s3, vpc, rds, elb, iam
from .services import lambda_
from .services import cost as cost_analysis
from .aws import aws_session

app = typer.Typer(help="AWS Super CLI – one-command resource visibility")
console = Console()

@app.command()
def ls(
    service: str = typer.Argument(..., help="Service to list (ec2, s3, vpc, rds, lambda, elb, iam)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Specific region to query"),
    all_regions: bool = typer.Option(True, "--all-regions/--no-all-regions", help="Query all regions (default) or current region only"),
    all_accounts: bool = typer.Option(False, "--all-accounts", help="Query all accessible AWS accounts"),
    accounts: Optional[str] = typer.Option(None, "--accounts", help="Comma-separated profiles or pattern (e.g., 'prod-*,staging')"),
    match: Optional[str] = typer.Option(None, "--match", "-m", help="Filter resources by name/tags (fuzzy match)"),
    columns: Optional[str] = typer.Option(None, "--columns", "-c", help="Comma-separated list of columns to display"),
    state: Optional[str] = typer.Option(None, "--state", help="Filter EC2 instances by state (running, stopped, etc.)"),
    instance_type: Optional[str] = typer.Option(None, "--instance-type", help="Filter EC2 instances by instance type"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter resources by tag (format: key=value)"),
    engine: Optional[str] = typer.Option(None, "--engine", help="Filter RDS instances by engine (mysql, postgres, etc.)"),
    runtime: Optional[str] = typer.Option(None, "--runtime", help="Filter Lambda functions by runtime (python, node, etc.)"),
    lb_type: Optional[str] = typer.Option(None, "--type", help="Filter load balancers by type (classic, application, network)"),
    iam_type: Optional[str] = typer.Option(None, "--iam-type", help="Filter IAM resources by type (users, roles, all)"),
):
    """List AWS resources across regions with beautiful output"""
    service_lower = service.lower()
    
    # Determine which profiles/accounts to query
    profiles_to_query = []
    
    if all_accounts:
        # Query all accessible accounts
        try:
            accounts_info = asyncio.run(aws_session.multi_account.discover_accounts())
            profiles_to_query = [acc['profile'] for acc in accounts_info]
            
            if not profiles_to_query:
                console.print("[yellow]No accessible AWS accounts found.[/yellow]")
                console.print("\n[dim]Run 'awsx accounts' to see available profiles[/dim]")
                return
                
            console.print(f"[dim]Querying {len(profiles_to_query)} accounts: {', '.join(profiles_to_query)}[/dim]")
            
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
            console.print("\n[dim]Run 'awsx accounts' to see available profiles[/dim]")
            return
            
        console.print(f"[dim]Querying accounts: {', '.join(profiles_to_query)}[/dim]")
    else:
        # Single account (current profile)
        profiles_to_query = None  # Will use current profile by default
    
    # Determine regions to query
    if region:
        regions_to_query = [region]
    elif all_regions:
        regions_to_query = aws_session.get_available_regions(service_lower)
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
        # Call the appropriate service
        if service_lower == "ec2":
            if profiles_to_query:
                # Multi-account call
                async def run_multi_account():
                    return await aws_session.multi_account.call_service_multi_account(
                        'ec2', 'describe_instances',
                        profiles=profiles_to_query,
                        regions=regions_to_query
                    )
                
                responses = asyncio.run(run_multi_account())
                instances = ec2.format_ec2_data_multi_account(responses)
            else:
                # Single account call
                instances = asyncio.run(ec2.list_ec2_instances(
                    regions=regions_to_query,
                    all_regions=all_regions,
                    match=match,
                    state=state,
                    instance_type=instance_type,
                    tag=tag
                ))
                
            # Apply filters
            if match or state or instance_type or tag:
                instances = ec2.apply_ec2_filters(instances, match, state, instance_type, tag)
            
            if not instances:
                console.print("[yellow]No EC2 instances found with the specified criteria.[/yellow]")
                return
            
            # Handle columns
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = ec2.create_ec2_table(instances, column_list)
            console.print(table)
            
            # Show summary with account info if multi-account
            if profiles_to_query:
                account_count = len(set(instance.get('Account', 'Unknown') for instance in instances))
                region_count = len(set(instance['Region'] for instance in instances))
                console.print(f"\n[green]Found {len(instances)} EC2 instances across {account_count} accounts and {region_count} regions[/green]")
            else:
                console.print(f"\n[green]Found {len(instances)} EC2 instances[/green]")
            
        elif service_lower == "s3":
            buckets = asyncio.run(s3.list_s3_buckets(
                regions=[region] if region else None,
                all_regions=all_regions,
                match=match
            ))
            
            if not buckets:
                console.print("[yellow]No S3 buckets found with the specified criteria.[/yellow]")
                return
            
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = s3.create_s3_table(buckets, column_list)
            console.print(table)
            console.print(f"\n[green]Found {len(buckets)} S3 buckets[/green]")
            
        elif service_lower == "vpc":
            vpcs = asyncio.run(vpc.list_vpcs(
                regions=[region] if region else None,
                all_regions=all_regions,
                match=match
            ))
            
            if not vpcs:
                console.print("[yellow]No VPCs found with the specified criteria.[/yellow]")
                return
            
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = vpc.create_vpc_table(vpcs, column_list)
            console.print(table)
            console.print(f"\n[green]Found {len(vpcs)} VPCs[/green]")

        elif service_lower == "rds":
            instances = asyncio.run(rds.list_rds_instances(
                regions=[region] if region else None,
                all_regions=all_regions,
                match=match,
                engine=engine
            ))
            
            if not instances:
                console.print("[yellow]No RDS instances found with the specified criteria.[/yellow]")
                return
            
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = rds.create_rds_table(instances, column_list)
            console.print(table)
            console.print(f"\n[green]Found {len(instances)} RDS instances[/green]")

        elif service_lower == "lambda":
            functions = asyncio.run(lambda_.list_lambda_functions(
                regions=[region] if region else None,
                all_regions=all_regions,
                match=match,
                runtime=runtime
            ))
            
            if not functions:
                console.print("[yellow]No Lambda functions found with the specified criteria.[/yellow]")
                return
            
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = lambda_.create_lambda_table(functions, column_list)
            console.print(table)
            console.print(f"\n[green]Found {len(functions)} Lambda functions[/green]")
            
        elif service_lower == "elb":
            load_balancers = asyncio.run(elb.list_load_balancers(
                regions=[region] if region else None,
                all_regions=all_regions,
                match=match,
                lb_type=lb_type
            ))
            
            if not load_balancers:
                console.print("[yellow]No load balancers found with the specified criteria.[/yellow]")
                return
            
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = elb.create_elb_table(load_balancers, column_list)
            console.print(table)
            console.print(f"\n[green]Found {len(load_balancers)} load balancers[/green]")
            
        elif service_lower == "iam":
            resources = asyncio.run(iam.list_iam_resources(
                match=match,
                resource_type=iam_type or 'all'
            ))
            
            if not resources:
                console.print("[yellow]No IAM resources found with the specified criteria.[/yellow]")
                return
            
            column_list = None
            if columns:
                column_list = [col.strip() for col in columns.split(',')]
            
            table = iam.create_iam_table(resources, column_list)
            console.print(table)
            console.print(f"\n[green]Found {len(resources)} IAM resources[/green]")
            
        else:
            console.print(f"[red]Multi-account support for {service} coming soon![/red]")
            console.print("[cyan]Multi-account support currently available for: ec2[/cyan]")
            console.print("[yellow]Single-account support available for: s3, vpc, rds, lambda, elb, iam[/yellow]")
            console.print("\n[bold]Examples:[/bold]")
            console.print("  awsx ls ec2 --all-accounts        # Multi-account EC2 (works now!)")
            console.print("  awsx ls s3                        # Single-account S3")
            console.print("  awsx ls rds --engine postgres     # Single-account RDS")
            console.print("  awsx accounts                     # List available profiles")
            return

    except Exception as e:
        console.print(f"[red]Error listing resources: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            console.print("")
            for message in help_messages:
                console.print(message)
        raise typer.Exit(1)


@app.command()
def cost(
    command: str = typer.Argument(..., help="Cost command (top-spend, by-account, daily, summary)"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze (default: 30)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of results to show (default: 10)"),
):
    """Analyze AWS costs and spending patterns"""
    command_lower = command.lower()
    
    try:
        if command_lower == "top-spend":
            console.print(f"[cyan]Analyzing top spending services for the last {days} days...[/cyan]")
            
            services_cost = asyncio.run(cost_analysis.get_cost_by_service(days=days, limit=limit))
            if not services_cost:
                console.print("[yellow]No cost data available. Check permissions and try again.[/yellow]")
                return
            
            table = cost_analysis.create_cost_table(
                services_cost, 
                f"Top {len(services_cost)} AWS Services by Cost (Last {days} days)"
            )
            console.print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in services_cost)
            console.print(f"\n[green]Total cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
        elif command_lower == "by-account":
            console.print(f"[cyan]Analyzing costs by account for the last {days} days...[/cyan]")
            
            accounts_cost = asyncio.run(cost_analysis.get_cost_by_account(days=days))
            if not accounts_cost:
                console.print("[yellow]No account cost data available.[/yellow]")
                return
            
            table = cost_analysis.create_cost_table(
                accounts_cost[:limit], 
                f"AWS Costs by Account (Last {days} days)"
            )
            console.print(table)
            
            total_shown = sum(item['Raw_Cost'] for item in accounts_cost[:limit])
            console.print(f"\n[green]Total cost shown: {cost_analysis.format_cost_amount(str(total_shown))}[/green]")
            
        elif command_lower == "daily":
            console.print("[cyan]Analyzing daily cost trends...[/cyan]")
            
            daily_costs = asyncio.run(cost_analysis.get_daily_costs(days=days))
            if not daily_costs:
                console.print("[yellow]No daily cost data available.[/yellow]")
                return
            
            table = cost_analysis.create_cost_table(
                daily_costs, 
                "Daily Cost Trend (Last 7 days)"
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
            
            summary = asyncio.run(cost_analysis.get_cost_summary(days=days))
            
            console.print("\n[bold]Cost Summary[/bold]")
            console.print(f"Period: {summary['period']}")
            console.print(f"Total Cost: [green]{summary['total_cost']}[/green]")
            console.print(f"Daily Average: [blue]{summary['daily_avg']}[/blue]")
            console.print(f"Trend: {summary['trend']}")
            
        else:
            console.print(f"[red]Unknown cost command: {command}[/red]")
            console.print("\n[bold]Available commands:[/bold]")
            console.print("  awsx cost top-spend      # Show top spending services")
            console.print("  awsx cost by-account     # Show costs by account")
            console.print("  awsx cost daily          # Show daily cost trends")
            console.print("  awsx cost summary        # Show overall cost summary")
            console.print("\n[bold]Options:[/bold]")
            console.print("  --days 7                 # Analyze last 7 days")
            console.print("  --limit 5                # Show top 5 results")
            
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
    """Show awsx version and current AWS context"""
    from . import __version__
    
    rprint(f"[bold cyan]awsx[/bold cyan] version {__version__}")
    
    # Show AWS context
    try:
        has_creds, account_id, error = aws_session.check_credentials()
        
        if has_creds and account_id:
            # Working credentials
            credential_source = aws_session.detect_credential_source()
            rprint(f"[dim]AWS Context:[/dim]")
            rprint(f"  Account: {account_id}")
            rprint(f"  Credentials: {credential_source}")
            
            # Show current region
            import boto3
            session = boto3.Session()
            region = session.region_name or 'us-east-1'
            rprint(f"  Default Region: {region}")
            
        elif has_creds and error:
            # Credentials exist but are invalid/expired
            credential_source = aws_session.detect_credential_source()
            rprint(f"[yellow]AWS credentials found ({credential_source}) but invalid/expired[/yellow]")
            rprint(f"[red]Error: {error}[/red]")
            rprint("")
            
            # Show helpful guidance
            help_messages = aws_session.get_credential_help(error)
            for message in help_messages:
                rprint(message)
        else:
            # No credentials
            rprint("[yellow]No AWS credentials configured[/yellow]")
            rprint("")
            help_messages = aws_session.get_credential_help(Exception("NoCredentialsError"))
            for message in help_messages:
                rprint(message)
                
    except Exception as e:
        rprint(f"[red]Error checking AWS context: {e}[/red]")


@app.command()
def test():
    """Test AWS connectivity and credentials"""
    rprint("[bold cyan]Testing AWS connectivity...[/bold cyan]")
    
    try:
        # Test credential detection
        has_creds, account_id, error = aws_session.check_credentials()
        
        if has_creds and account_id:
            credential_source = aws_session.detect_credential_source()
            rprint(f"✅ Credentials working: {credential_source}")
            rprint(f"✅ Account ID: {account_id}")
            
            # Test region detection
            import boto3
            session = boto3.Session()
            region = session.region_name or 'us-east-1'
            rprint(f"✅ Default region: {region}")
            
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
                    rprint(f"✅ EC2 API access working - found {instance_count} instances in {region}")
                else:
                    rprint(f"✅ EC2 API access working - no instances in {region}")
                    
            except Exception as e:
                rprint(f"❌ EC2 API error: {e}")
                help_messages = aws_session.get_credential_help(e)
                if help_messages:
                    rprint("")
                    for message in help_messages:
                        rprint(message)
            
        elif has_creds and error:
            rprint(f"❌ Credentials found but invalid: {error}")
            help_messages = aws_session.get_credential_help(error)
            if help_messages:
                rprint("")
                for message in help_messages:
                    rprint(message)
        else:
            rprint("❌ No AWS credentials found")
            help_messages = aws_session.get_credential_help(Exception("NoCredentialsError"))
            for message in help_messages:
                rprint(message)
                
    except Exception as e:
        rprint(f"❌ Unexpected error: {e}")


@app.command()
def accounts():
    """List available AWS accounts and profiles"""
    console.print("[bold cyan]🏢 Available AWS Accounts & Profiles[/bold cyan]")
    console.print()
    
    try:
        # Discover profiles
        profiles = aws_session.multi_account.discover_profiles()
        
        if not profiles:
            console.print("[yellow]No AWS profiles found.[/yellow]")
            console.print("\n[dim]Set up profiles with:[/dim]")
            console.print("  aws configure --profile mycompany")
            console.print("  aws configure sso")
            return
        
        # Test which profiles are accessible
        console.print("[dim]Testing profile accessibility...[/dim]")
        
        async def test_profiles():
            return await aws_session.multi_account.discover_accounts()
        
        accessible_accounts = asyncio.run(test_profiles())
        accessible_profile_names = {acc['profile'] for acc in accessible_accounts}
        
        from rich.table import Table
        table = Table(title="AWS Profiles", show_header=True, header_style="bold magenta")
        table.add_column("Profile", style="cyan", min_width=15)
        table.add_column("Type", style="blue", min_width=10)
        table.add_column("Account ID", style="green", min_width=12)
        table.add_column("Status", style="yellow", min_width=10)
        table.add_column("Description", min_width=30)
        
        for profile in profiles:
            profile_name = profile['name']
            
            # Find matching accessible account
            account_info = next((acc for acc in accessible_accounts if acc['profile'] == profile_name), None)
            
            if account_info:
                status = "[green]✓ Active[/green]"
                account_id = account_info['account_id']
            else:
                status = "[red]✗ Error[/red]"
                account_id = profile.get('account_id', 'Unknown')
            
            table.add_row(
                profile_name,
                profile['type'].title(),
                account_id,
                status,
                profile['description']
            )
        
        console.print(table)
        console.print(f"\n[green]Found {len(accessible_accounts)} accessible accounts across {len(profiles)} profiles[/green]")
        
        if accessible_accounts:
            console.print("\n[bold]Multi-account usage examples:[/bold]")
            console.print("  awsx ls ec2 --all-accounts           # Query all accessible accounts")
            console.print("  awsx ls s3 --accounts prod-*         # Query accounts matching pattern")
            console.print("  awsx cost top-spend                  # Analyze costs across accounts")
            
            # Show example with actual profile names
            example_profiles = [acc['profile'] for acc in accessible_accounts[:2]]
            if len(example_profiles) >= 2:
                console.print(f"  awsx ls vpc --accounts {','.join(example_profiles)} # Query specific accounts")
        
    except Exception as e:
        console.print(f"[red]Error discovering accounts: {e}[/red]")
        help_messages = aws_session.get_credential_help(e)
        if help_messages:
            console.print("")
            for message in help_messages:
                console.print(message)


if __name__ == "__main__":
    app() 