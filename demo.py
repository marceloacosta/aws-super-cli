#!/usr/bin/env python3
"""
AWS Super CLI (awsx) - Demo Script
Showcases all supported services and their capabilities
"""

import subprocess
import time
import sys
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

console = Console()

def run_awsx_command(cmd):
    """Run an awsx command and return success status"""
    try:
        result = subprocess.run(
            ["python", "-m", "awsx.cli"] + cmd.split(), 
            capture_output=True, 
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            console.print(f"[red]Error: {result.stderr}[/red]")
            return False
    except subprocess.TimeoutExpired:
        console.print("[yellow]Command timed out[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]Exception: {e}[/red]")
        return False

def demo_header():
    """Show demo header"""
    title = Text("AWS Super CLI (awsx) - Comprehensive Demo", style="bold blue")
    subtitle = Text("Discover your AWS empire across 7 major services", style="dim")
    
    console.print()
    console.print(Panel(f"{title}\n{subtitle}", 
                       title="🚀 awsx", 
                       title_align="center",
                       border_style="blue"))
    console.print()

def demo_service(service_name, description, commands):
    """Demo a specific service"""
    console.print(f"[bold cyan]📋 {service_name.upper()} Service[/bold cyan]")
    console.print(f"[dim]{description}[/dim]")
    console.print()
    
    for i, (cmd_desc, cmd) in enumerate(commands, 1):
        console.print(f"[yellow]{i}. {cmd_desc}[/yellow]")
        console.print(f"[dim]$ awsx {cmd}[/dim]")
        
        success = run_awsx_command(cmd)
        if not success:
            console.print("[red]⚠️ This service might not have resources in your account[/red]")
        
        console.print()
        if i < len(commands):
            time.sleep(1)  # Brief pause between commands
    
    console.print("─" * 80)
    console.print()

def main():
    """Run the comprehensive demo"""
    demo_header()
    
    # Check if awsx is available
    console.print("[dim]Checking awsx availability...[/dim]")
    if not run_awsx_command("--help > /dev/null 2>&1"):
        console.print("[red]❌ awsx not found. Please ensure it's installed.[/red]")
        sys.exit(1)
    
    console.print("[green]✅ awsx is ready![/green]")
    console.print()
    time.sleep(1)
    
    # Demo each service
    services = [
        ("EC2", "Virtual machines and compute instances", [
            ("List all EC2 instances across regions", "ls ec2"),
            ("Show only running instances", "ls ec2 --state running"),
            ("Find instances with 'prod' in name/tags", "ls ec2 --match prod")
        ]),
        
        ("S3", "Object storage buckets", [
            ("List all S3 buckets", "ls s3"),
            ("Find buckets with specific name pattern", "ls s3 --match zircon")
        ]),
        
        ("VPC", "Virtual Private Clouds and networking", [
            ("List all VPCs across regions", "ls vpc"),
            ("Show VPCs in specific region", "ls vpc --region us-east-1")
        ]),
        
        ("RDS", "Relational database instances", [
            ("List all RDS instances", "ls rds"),
            ("Show PostgreSQL instances only", "ls rds --engine postgres")
        ]),
        
        ("Lambda", "Serverless functions", [
            ("List all Lambda functions", "ls lambda"),
            ("Show Python functions only", "ls lambda --runtime python"),
            ("Find functions with specific name", "ls lambda --match boilerplate")
        ]),
        
        ("ELB", "Load balancers (Classic, Application, Network)", [
            ("List all load balancers", "ls elb"),
            ("Show Application Load Balancers only", "ls elb --type application")
        ]),
        
        ("IAM", "Identity and Access Management", [
            ("List all IAM users and roles", "ls iam"),
            ("Show IAM users only", "ls iam --iam-type users"),
            ("Show IAM roles only", "ls iam --iam-type roles")
        ])
    ]
    
    for service_name, description, commands in services:
        try:
            demo_service(service_name, description, commands)
            time.sleep(2)  # Pause between services
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted by user[/yellow]")
            break
    
    # Summary
    console.print("[bold green]🎉 Demo Complete![/bold green]")
    console.print()
    console.print("[cyan]AWS Super CLI supports:[/cyan]")
    console.print("• [blue]7 major AWS services[/blue] (EC2, S3, VPC, RDS, Lambda, ELB, IAM)")
    console.print("• [blue]Cross-region discovery[/blue] (--all-regions by default)")
    console.print("• [blue]Intelligent filtering[/blue] (--match, --state, --engine, etc.)")
    console.print("• [blue]Beautiful rich tables[/blue] with color-coded status")
    console.print("• [blue]Service-specific options[/blue] for advanced filtering")
    console.print()
    console.print("[dim]Get started: awsx ls <service> --help[/dim]")

if __name__ == "__main__":
    main() 