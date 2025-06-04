#!/usr/bin/env python3
"""
AWS Super CLI (aws-super-cli) - Demo Script
Demonstrates the capabilities of AWS Super CLI
"""

import asyncio
import subprocess
from typing import Dict, Any
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def run_aws_super_cli_command(cmd):
    """Run an aws-super-cli command and return success status"""
    try:
        result = subprocess.run(
            ["python", "-m", "awsx.cli"] + cmd.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            console.print(result.stdout)
        if result.stderr and result.returncode != 0:
            console.print(f"[red]{result.stderr}[/red]")
            
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


console = Console()

def show_header():
    """Show demo header"""
    title = Text("AWS Super CLI (aws-super-cli) - Comprehensive Demo", style="bold blue")
    panel = Panel(
        title,
        title="aws-super-cli",
        border_style="blue",
        padding=(1, 2)
    )
    console.print()
    console.print(panel)
    console.print()


def demo_command(cmd: str, description: str, show_output: bool = True):
    """Demo a command with description"""
    console.print(f"\n[cyan]■ {description}[/cyan]")
    
    if show_output:
        console.print(f"[dim]$ aws-super-cli {cmd}[/dim]")
        
        success = run_aws_super_cli_command(cmd)
        
        if not success:
            console.print("[red]Command failed or had issues[/red]")
        
        time.sleep(1)  # Brief pause for readability
    else:
        console.print(f"[dim]Command: aws-super-cli {cmd}[/dim]")


def check_prerequisites():
    """Check if AWS Super CLI is available"""
    console.print("[bold]Prerequisites Check[/bold]")
    
    # Check if aws-super-cli is available
    console.print("[dim]Checking aws-super-cli availability...[/dim]")
    if not run_aws_super_cli_command("--help > /dev/null 2>&1"):
        console.print("[red]❌ aws-super-cli not found. Please ensure it's installed.[/red]")
        console.print("[yellow]Install with: pip install aws-super-cli[/yellow]")
        return False
    
    console.print("[green]✅ aws-super-cli is ready![/green]")
    
    return True


def main():
    """Run comprehensive demo"""
    show_header()
    
    if not check_prerequisites():
        return
        
    console.print("[bold]🚀 AWS Super CLI Demonstration[/bold]")
    console.print()
    
    # System Information
    console.print("[bold yellow]═══ System Information ═══[/bold yellow]")
    demo_command("version", "Check AWS Super CLI version and AWS credentials")
    demo_command("test", "Test AWS connectivity and permissions")
    
    # Account Discovery  
    console.print("\n[bold yellow]═══ Account & Profile Discovery ═══[/bold yellow]")
    demo_command("accounts", "List available AWS accounts and profiles")
    
    # Resource Discovery
    console.print("\n[bold yellow]═══ Resource Discovery ═══[/bold yellow]")
    demo_command("ls ec2", "List EC2 instances")
    demo_command("ls s3", "List S3 buckets")
    demo_command("ls iam --iam-type users", "List IAM users")
    demo_command("ls rds", "List RDS instances")
    demo_command("ls lambda", "List Lambda functions")
    
    # Multi-Account Queries (if available)
    console.print("\n[bold yellow]═══ Multi-Account Capabilities ═══[/bold yellow]")
    demo_command("ls ec2 --all-accounts", "List EC2 instances across all accounts", show_output=False)
    console.print("[dim]Note: This requires multiple AWS profiles configured[/dim]")
    
    # Security Auditing
    console.print("\n[bold yellow]═══ Security Auditing ═══[/bold yellow]")
    demo_command("audit --summary", "Run comprehensive security audit")
    demo_command("audit --services network", "Network security audit only", show_output=False)
    demo_command("audit --services s3", "S3 security audit only", show_output=False)
    
    # Cost Analysis
    console.print("\n[bold yellow]═══ Cost Analysis ═══[/bold yellow]")
    demo_command("cost summary", "Get cost summary with trends")
    demo_command("cost top-spend", "Show top spending services", show_output=False)
    demo_command("cost credits", "Analyze credit usage", show_output=False)
    
    # Advanced Features
    console.print("\n[bold yellow]═══ Advanced Features ═══[/bold yellow]")
    demo_command("help", "Show comprehensive help", show_output=False)
    console.print("[dim]Additional advanced options:[/dim]")
    console.print("[dim]• Filtering: --state, --engine, --runtime, --match[/dim]")
    console.print("[dim]• Regions: --region, --all-regions[/dim]")
    console.print("[dim]• Debug: --debug for troubleshooting[/dim]")
    
    # Summary
    console.print("\n[bold green]═══ Demo Complete ═══[/bold green]")
    console.print("[green]✅ AWS Super CLI demonstration finished![/green]")
    console.print()
    console.print("[bold]Key Capabilities Demonstrated:[/bold]")
    console.print("• 🔒 Security auditing across S3, IAM, and network infrastructure")
    console.print("• 🔍 Multi-account resource discovery")
    console.print("• 💰 Cost analysis with credit tracking")
    console.print("• 📊 Beautiful rich table output")
    console.print("• ⚡ Parallel multi-account queries")
    console.print()
    console.print("[dim]Get started: aws-super-cli ls <service> --help[/dim]")


if __name__ == "__main__":
    main() 