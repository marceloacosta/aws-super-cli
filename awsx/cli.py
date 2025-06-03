import asyncio
from typing import List, Optional
import typer
from rich.console import Console
from rich import print as rprint

from .services.ec2 import list_ec2_instances, create_ec2_table
from .aws import aws_session

app = typer.Typer(help="AWS Super CLI – one-command resource visibility")
console = Console()

@app.command()
def ls(
    service: str = typer.Argument(help="AWS service to list (e.g., ec2, s3, rds)"),
    all_regions: bool = typer.Option(False, "--all-regions", help="Query all AWS regions"),
    regions: Optional[List[str]] = typer.Option(None, "--region", help="Specific regions to query"),
    match: Optional[str] = typer.Option(None, "--match", help="Fuzzy search filter"),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state (e.g., running, stopped)"),
    columns: Optional[str] = typer.Option(None, "--columns", help="Comma-separated list of columns to display"),
    tag: Optional[List[str]] = typer.Option(None, "--tag", help="Filter by tag (format: key=value)"),
):
    """
    List AWS resources across accounts/regions with beautiful output.
    
    Examples:
      awsx ls ec2
      awsx ls ec2 --all-regions --match prod
      awsx ls ec2 --state running --tag Environment=prod
      awsx ls ec2 --columns instance-id,name,state,type
    """
    
    # Parse tag filters
    tag_filters = {}
    if tag:
        for tag_str in tag:
            if '=' in tag_str:
                key, value = tag_str.split('=', 1)
                tag_filters[key] = value
            else:
                rprint(f"[red]Invalid tag format: {tag_str}. Use key=value format.[/red]")
                raise typer.Exit(1)
    
    # Parse columns
    column_list = None
    if columns:
        # Map common column aliases to full names
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
                    rprint(f"[yellow]Warning: Unknown column '{col}'. Available columns: {', '.join(column_map.keys())}[/yellow]")
    
    if service.lower() == 'ec2':
        try:
            # Show which credentials we're using
            credential_source = aws_session.detect_credential_source()
            account_id = aws_session.get_current_account()
            if account_id:
                rprint(f"[dim]Using {credential_source} (Account: {account_id})[/dim]")
            
            # Run the async function
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
    
    else:
        rprint(f"[yellow]Service '{service}' not yet supported. Currently supported: ec2[/yellow]")
        rprint("[dim]Coming soon: s3, rds, lambda, and more![/dim]")


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


if __name__ == "__main__":
    app() 