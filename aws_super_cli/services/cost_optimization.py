"""
AWS Cost Optimization Toolkit - Core Infrastructure
Provides foundation for cost optimization features including directory management,
configuration, error handling, and AWS service integration framework.
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from ..aws import aws_session


@dataclass
class OptimizationConfig:
    """Configuration for cost optimization toolkit"""
    output_directory: str = "~/aws-savings"
    enable_auto_enrollment: bool = True
    support_plan_check: bool = True
    iam_policy_check: bool = True
    file_retention_days: int = 90
    export_formats: List[str] = None
    
    def __post_init__(self):
        if self.export_formats is None:
            self.export_formats = ["json", "csv"]
        
        # Expand user directory
        self.output_directory = os.path.expanduser(self.output_directory)


@dataclass
class OptimizationRecommendation:
    """Standard structure for cost optimization recommendations"""
    service: str
    resource_id: str
    resource_type: str
    recommendation_type: str
    current_cost: float
    estimated_savings: float
    confidence: str  # HIGH, MEDIUM, LOW
    description: str
    remediation_steps: List[str]
    region: str
    account_id: str
    timestamp: str
    source: str  # trusted_advisor, compute_optimizer, cost_explorer, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return asdict(self)


class CostOptimizationCore:
    """Core infrastructure for AWS Cost Optimization Toolkit"""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.console = Console()
        self._ensure_output_directory()
        
    def _ensure_output_directory(self) -> None:
        """Ensure output directory exists"""
        try:
            Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)
            self.console.print(f"[dim]Output directory: {self.config.output_directory}[/dim]")
        except Exception as e:
            self.console.print(f"[red]Error creating output directory: {e}[/red]")
            raise
    
    def get_timestamped_filename(self, service: str, format: str = "json") -> str:
        """Generate timestamped filename for service recommendations"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{service}-{timestamp}.{format}"
        return os.path.join(self.config.output_directory, filename)
    
    def save_recommendations(self, recommendations: List[OptimizationRecommendation], 
                           service: str) -> Dict[str, str]:
        """Save recommendations to timestamped files in configured formats"""
        saved_files = {}
        
        try:
            # Convert recommendations to dictionaries
            data = [rec.to_dict() for rec in recommendations]
            
            for format in self.config.export_formats:
                filename = self.get_timestamped_filename(service, format)
                
                if format == "json":
                    self._save_json(data, filename)
                elif format == "csv":
                    self._save_csv(data, filename)
                
                saved_files[format] = filename
                self.console.print(f"[green]Saved {len(recommendations)} recommendations to {filename}[/green]")
        
        except Exception as e:
            self.console.print(f"[red]Error saving recommendations: {e}[/red]")
            raise
        
        return saved_files
    
    def _save_json(self, data: List[Dict], filename: str) -> None:
        """Save data as JSON with proper formatting"""
        with open(filename, 'w') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_recommendations": len(data),
                "recommendations": data
            }, f, indent=2, default=str)
    
    def _save_csv(self, data: List[Dict], filename: str) -> None:
        """Save data as CSV with headers"""
        if not data:
            return
        
        import csv
        
        # Get all possible fieldnames from all records
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    async def get_account_info(self) -> Dict[str, str]:
        """Get current AWS account information"""
        try:
            session = aws_session.session
            sts_client = session.client('sts')
            
            identity = sts_client.get_caller_identity()
            
            return {
                "account_id": identity.get('Account', 'unknown'),
                "user_arn": identity.get('Arn', 'unknown'),
                "user_id": identity.get('UserId', 'unknown')
            }
        except Exception as e:
            self.console.print(f"[red]Error getting account info: {e}[/red]")
            return {
                "account_id": "unknown",
                "user_arn": "unknown", 
                "user_id": "unknown"
            }
    
    async def check_iam_permissions(self, required_policies: List[str]) -> Dict[str, bool]:
        """Check if current user has required IAM policies"""
        results = {}
        
        try:
            session = aws_session.session
            iam_client = session.client('iam')
            sts_client = session.client('sts')
            
            # Get current user/role
            identity = sts_client.get_caller_identity()
            arn = identity.get('Arn', '')
            
            if ':user/' in arn:
                # It's a user
                username = arn.split('/')[-1]
                user_policies = iam_client.list_attached_user_policies(UserName=username)
                attached_policies = [p['PolicyArn'] for p in user_policies['AttachedPolicies']]
            elif ':role/' in arn:
                # It's a role
                role_name = arn.split('/')[-1]
                role_policies = iam_client.list_attached_role_policies(RoleName=role_name)
                attached_policies = [p['PolicyArn'] for p in role_policies['AttachedPolicies']]
            else:
                attached_policies = []
            
            # Check each required policy
            for policy in required_policies:
                # Handle both full ARNs and policy names
                if policy.startswith('arn:aws:iam::aws:policy/'):
                    results[policy] = policy in attached_policies
                else:
                    # Convert policy name to full ARN
                    full_arn = f"arn:aws:iam::aws:policy/{policy}"
                    results[policy] = full_arn in attached_policies
        
        except Exception as e:
            self.console.print(f"[red]Error checking IAM permissions: {e}[/red]")
            # Default to False for all policies on error
            for policy in required_policies:
                results[policy] = False
        
        return results
    
    async def check_support_plan(self) -> Dict[str, Any]:
        """Check AWS Support Plan tier"""
        try:
            session = aws_session.session
            support_client = session.client('support', region_name='us-east-1')
            
            # Try to describe support cases to determine support plan
            try:
                support_client.describe_cases(maxResults=1)
                # If this succeeds, we have at least Basic support
                
                # Try to get Trusted Advisor checks to determine plan level
                try:
                    checks = support_client.describe_trusted_advisor_checks(language='en')
                    # If we can get checks, we have Business or Enterprise
                    return {
                        "has_support": True,
                        "plan_tier": "Business/Enterprise",
                        "trusted_advisor_available": True,
                        "message": "Business or Enterprise support plan detected"
                    }
                except Exception:
                    # Basic or Developer plan
                    return {
                        "has_support": True,
                        "plan_tier": "Basic/Developer", 
                        "trusted_advisor_available": False,
                        "message": "Basic or Developer support plan detected"
                    }
            
            except Exception:
                return {
                    "has_support": False,
                    "plan_tier": "None",
                    "trusted_advisor_available": False,
                    "message": "No support plan or insufficient permissions"
                }
        
        except Exception as e:
            return {
                "has_support": False,
                "plan_tier": "Unknown",
                "trusted_advisor_available": False,
                "message": f"Error checking support plan: {e}"
            }
    
    def create_prerequisites_table(self, account_info: Dict, iam_results: Dict, 
                                 support_info: Dict) -> Table:
        """Create a table showing prerequisites status"""
        table = Table(title="Cost Optimization Prerequisites")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        
        # Account info
        table.add_row(
            "AWS Account",
            "✓ Connected" if account_info.get('account_id') != 'unknown' else "✗ Error",
            f"Account: {account_info.get('account_id', 'unknown')}"
        )
        
        # IAM permissions
        for policy, has_permission in iam_results.items():
            policy_name = policy.split('/')[-1] if '/' in policy else policy
            status = "✓ Attached" if has_permission else "✗ Missing"
            table.add_row(
                f"IAM Policy: {policy_name}",
                status,
                "Required for cost optimization features"
            )
        
        # Support plan
        support_status = "✓ Available" if support_info.get('trusted_advisor_available') else "✗ Unavailable"
        table.add_row(
            "Support Plan",
            support_status,
            support_info.get('message', 'Unknown')
        )
        
        return table
    
    def cleanup_old_files(self) -> int:
        """Clean up old recommendation files based on retention policy"""
        if self.config.file_retention_days <= 0:
            return 0
        
        try:
            output_dir = Path(self.config.output_directory)
            if not output_dir.exists():
                return 0
            
            cutoff_date = datetime.now().timestamp() - (self.config.file_retention_days * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in output_dir.glob("*-????-??-??.json"):
                if file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
            
            for file_path in output_dir.glob("*-????-??-??.csv"):
                if file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                self.console.print(f"[dim]Cleaned up {deleted_count} old files[/dim]")
            
            return deleted_count
        
        except Exception as e:
            self.console.print(f"[red]Error during cleanup: {e}[/red]")
            return 0


class OptimizationError(Exception):
    """Custom exception for cost optimization errors"""
    
    def __init__(self, message: str, error_code: str = None, remediation: str = None):
        self.message = message
        self.error_code = error_code
        self.remediation = remediation
        super().__init__(self.message)


def handle_optimization_error(error: Exception, console: Console) -> None:
    """Handle and display optimization errors with helpful guidance"""
    if isinstance(error, OptimizationError):
        console.print(f"[red]Cost Optimization Error: {error.message}[/red]")
        if error.error_code:
            console.print(f"[dim]Error Code: {error.error_code}[/dim]")
        if error.remediation:
            console.print(f"[yellow]Remediation: {error.remediation}[/yellow]")
    else:
        console.print(f"[red]Unexpected error: {error}[/red]")
        console.print("[yellow]Please check your AWS credentials and permissions[/yellow]")


# Global instance for easy access
cost_optimization_core = CostOptimizationCore() 