import asyncio
from typing import List, Optional
import typer
from rich.console import Console
from rich import print as rprint

from .services.ec2 import list_ec2_instances, create_ec2_table
from .services.s3 import list_s3_buckets, create_s3_table
from .services.vpc import list_vpcs, create_vpc_table
from .aws import aws_session

app = typer.Typer(help="AWS Super CLI – one-command resource visibility")
console = Console()

@app.command()
def ls(
    service: str = typer.Argument(help="AWS service to list (e.g., ec2, s3, vpc, rds)"),
    all_regions: bool = typer.Option(True, "--all-regions/--no-all-regions", help="Query all AWS regions (default: True)"),
    regions: Optional[List[str]] = typer.Option(None, "--region", help="Specific regions to query (overrides --all-regions)"),
    match: Optional[str] = typer.Option(None, "--match", help="Fuzzy search filter"),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state (e.g., running, stopped)"),
    columns: Optional[str] = typer.Option(None, "--columns", help="Comma-separated list of columns to display"),
    tag: Optional[List[str]] = typer.Option(None, "--tag", help="Filter by tag (format: key=value)"),
):
    """
    List AWS resources across accounts/regions with beautiful output.
    
    By default, searches ALL regions for maximum discovery.
    Use --region to limit to specific regions, or --no-all-regions for current region only.
    
    Examples:
      awsx ls ec2                           # All regions (default)
      awsx ls ec2 --region us-west-2        # Specific region only
      awsx ls ec2 --no-all-regions          # Current region only  
      awsx ls ec2 --match prod              # All regions, filter by "prod"
      awsx ls ec2 --state running           # All regions, running instances only
      awsx ls vpc                           # All VPCs across all regions
      awsx ls s3 --match zircon             # All S3 buckets with "zircon" in name
    """
    
    # Check if service is supported first
    supported_services = ['ec2', 's3', 'vpc']
    if service.lower() not in supported_services:
        rprint(f"[yellow]Service '{service}' not yet supported. Currently supported: {', '.join(supported_services)}[/yellow]")
        rprint("[dim]Coming soon: rds, lambda, iam, and more![/dim]")
        raise typer.Exit(1)

    # Parse tag filters (relevant for ec2 and vpc)
    tag_filters = {}
    if tag and service.lower() in ['ec2', 'vpc']:
        for tag_str in tag:
            if '=' in tag_str:
                key, value = tag_str.split('=', 1)
                tag_filters[key] = value
            else:
                rprint(f"[red]Invalid tag format: {tag_str}. Use key=value format.[/red]")
                raise typer.Exit(1)
    elif tag and service.lower() not in ['ec2', 'vpc']:
        rprint(f"[yellow]Tag filtering not supported for {service} service[/yellow]")
    
    # State filtering only supported for EC2
    if state and service.lower() != 'ec2':
        rprint(f"[yellow]State filtering only supported for EC2 service[/yellow]")
    
    # Parse columns
    column_list = None
    if columns:
        if service.lower() == 'ec2':
            # Map common column aliases to full names for EC2
            column_map = {
                'instance-id': 'Instance ID',
                'id': 'Instance ID',
                'name': 'Name',
                'state': 'State',
                'type': 'Type',
                'region': 'Region',
                'az': 'AZ',
                'private-ip': 'Private IP',
                'public-ip': 'Public IP',
                'tags': 'Tags'
            }
        elif service.lower() == 's3':
            # Map common column aliases for S3
            column_map = {
                'bucket': 'Bucket Name',
                'name': 'Bucket Name',
                'bucket-name': 'Bucket Name',
                'region': 'Region',
                'created': 'Created',
                'encryption': 'Encryption',
                'versioning': 'Versioning',
                'public': 'Public Access'
            }
        elif service.lower() == 'vpc':
            # Map common column aliases for VPC
            column_map = {
                'vpc-id': 'VPC ID',
                'id': 'VPC ID',
                'name': 'Name',
                'cidr': 'CIDR',
                'state': 'State',
                'default': 'Default',
                'region': 'Region',
                'tenancy': 'Tenancy',
                'tags': 'Tags'
            }
        else:
            column_map = {}
        
        column_list = []
        for col in columns.split(','):
            col = col.strip().lower()
            if col in column_map:
                column_list.append(column_map[col])
            else:
                # Try to find a case-insensitive match
                found = False
                for key, value in column_map.items():
                    if col == value.lower():
                        column_list.append(value)
                        found = True
                        break
                if not found:
                    available_cols = ', '.join(column_map.keys())
                    rprint(f"[yellow]Warning: Unknown column '{col}' for {service}. Available: {available_cols}[/yellow]")

    # Check credentials first (common for all services)
    has_creds, account_id, error = aws_session.check_credentials()
    
    if has_creds and account_id:
        # Working credentials
        credential_source = aws_session.detect_credential_source()
        rprint(f"[dim]Using {credential_source} (Account: {account_id})[/dim]")
    elif has_creds and error:
        # Credentials exist but are invalid/expired  
        rprint(f"[red]Error: {error}[/red]")
        help_messages = aws_session.get_credential_help(error)
        if help_messages:
            rprint("")
            for message in help_messages:
                rprint(message)
        raise typer.Exit(1)
    else:
        # No credentials
        rprint("[red]No AWS credentials found[/red]")
        help_messages = aws_session.get_credential_help(Exception("NoCredentialsError"))
        if help_messages:
            rprint("")
            for message in help_messages:
                rprint(message)
        raise typer.Exit(1)

    # Handle different services
    if service.lower() == 'ec2':
        # Run the EC2 async function
        try:
            instances = asyncio.run(list_ec2_instances(
                regions=regions,
                all_regions=all_regions,
                match=match,
                state=state,
                tag_filters=tag_filters or None
            ))
            
            if not instances:
                rprint("[yellow]No EC2 instances found matching the criteria.[/yellow]")
                return
            
            # Create and display the table
            table = create_ec2_table(instances, columns=column_list)
            console.print(table)
            
            # Show summary
            region_count = len(set(instance['Region'] for instance in instances))
            rprint(f"\n[dim]Found {len(instances)} instances across {region_count} region(s)[/dim]")
            
        except Exception as e:
            rprint(f"[red]Error listing EC2 instances: {e}[/red]")
            
            # Show helpful credential guidance
            help_messages = aws_session.get_credential_help(e)
            if help_messages:
                rprint("")
                for message in help_messages:
                    rprint(message)
            
            raise typer.Exit(1)
    
    elif service.lower() == 's3':
        # Run the S3 async function
        try:
            buckets = asyncio.run(list_s3_buckets(
                match=match,
                regions=regions,
                all_regions=all_regions
            ))
            
            if not buckets:
                rprint("[yellow]No S3 buckets found matching the criteria.[/yellow]")
                return
            
            # Create and display the table
            table = create_s3_table(buckets, columns=column_list)
            console.print(table)
            
            # Show summary
            region_count = len(set(bucket['Region'] for bucket in buckets))
            rprint(f"\n[dim]Found {len(buckets)} buckets across {region_count} region(s)[/dim]")
            
        except Exception as e:
            rprint(f"[red]Error listing S3 buckets: {e}[/red]")
            
            # Show helpful credential guidance
            help_messages = aws_session.get_credential_help(e)
            if help_messages:
                rprint("")
                for message in help_messages:
                    rprint(message)
            
            raise typer.Exit(1)
    
    elif service.lower() == 'vpc':
        # Run the VPC async function
        try:
            vpcs = asyncio.run(list_vpcs(
                regions=regions,
                all_regions=all_regions,
                match=match,
                tag_filters=tag_filters or None
            ))
            
            if not vpcs:
                rprint("[yellow]No VPCs found matching the criteria.[/yellow]")
                return
            
            # Create and display the table
            table = create_vpc_table(vpcs, columns=column_list)
            console.print(table)
            
            # Show summary
            region_count = len(set(vpc['Region'] for vpc in vpcs))
            rprint(f"\n[dim]Found {len(vpcs)} VPCs across {region_count} region(s)[/dim]")
            
        except Exception as e:
            rprint(f"[red]Error listing VPCs: {e}[/red]")
            
            # Show helpful credential guidance
            help_messages = aws_session.get_credential_help(e)
            if help_messages:
                rprint("")
                for message in help_messages:
                    rprint(message)
            
            raise typer.Exit(1)
    
    else:
        # This should never be reached since we check supported services at the top
        rprint(f"[red]Unexpected error: Unknown service '{service}'[/red]")
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


if __name__ == "__main__":
    app() 