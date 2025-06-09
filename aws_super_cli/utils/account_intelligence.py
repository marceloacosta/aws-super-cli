"""Account Intelligence - Smart AWS account management and categorization"""

import asyncio
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum

import boto3
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError
from rich.console import Console
from rich.table import Table


class AccountCategory(Enum):
    """Smart account categorization"""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    SANDBOX = "sandbox"
    SECURITY = "security"
    SHARED_SERVICES = "shared-services"
    BACKUP = "backup"
    LOGGING = "logging"
    UNKNOWN = "unknown"


class AccountHealth(Enum):
    """Account health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class AccountProfile:
    """Enhanced account profile with intelligence"""
    name: str
    account_id: str
    type: str
    region: str
    status: str
    category: AccountCategory
    health: AccountHealth
    nickname: Optional[str] = None
    description: str = ""
    last_activity: Optional[datetime] = None
    cost_last_30_days: float = 0.0
    resource_count: int = 0
    security_score: int = 0
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class AccountIntelligence:
    """Smart account management and categorization"""
    
    def __init__(self):
        self.console = Console()
        self.cache_file = Path.home() / '.aws-super-cli' / 'account_cache.json'
        self.cache_file.parent.mkdir(exist_ok=True)
        self._accounts_cache = None
        
        # Categorization patterns
        self.category_patterns = {
            AccountCategory.PRODUCTION: [
                r'prod', r'production', r'live', r'main', r'master'
            ],
            AccountCategory.STAGING: [
                r'stag', r'staging', r'stage', r'pre-prod', r'preprod', r'uat'
            ],
            AccountCategory.DEVELOPMENT: [
                r'dev', r'develop', r'development', r'test', r'testing'
            ],
            AccountCategory.SANDBOX: [
                r'sandbox', r'sb', r'playground', r'experiment', r'trial'
            ],
            AccountCategory.SECURITY: [
                r'security', r'sec', r'audit', r'compliance', r'governance'
            ],
            AccountCategory.SHARED_SERVICES: [
                r'shared', r'common', r'core', r'platform', r'infra', r'infrastructure'
            ],
            AccountCategory.BACKUP: [
                r'backup', r'bak', r'archive', r'disaster', r'dr'
            ],
            AccountCategory.LOGGING: [
                r'log', r'logging', r'logs', r'monitoring', r'observability'
            ]
        }
    
    def categorize_account(self, profile_name: str, account_id: str = None, description: str = "") -> AccountCategory:
        """Intelligently categorize an AWS account"""
        searchable_text = f"{profile_name} {description}".lower()
        
        # Check each category pattern
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, searchable_text):
                    return category
        
        return AccountCategory.UNKNOWN
    
    async def check_account_health(self, profile_name: str) -> Tuple[AccountHealth, List[str]]:
        """Perform comprehensive account health check"""
        issues = []
        service_details = []
        
        try:
            # Create session for this profile
            session_kwargs = {} if profile_name == 'default' else {'profile_name': profile_name}
            session = boto3.Session(**session_kwargs)
            
            # Test basic connectivity
            try:
                sts = session.client('sts')
                identity = sts.get_caller_identity()
                service_details.append("✓ Authentication: Successful")
            except (ClientError, NoCredentialsError) as e:
                error_msg = f"Authentication failed: {str(e)}"
                issues.append(error_msg)
                service_details.append(f"✗ Authentication: {error_msg}")
                return AccountHealth.ERROR, issues
            
            # Check multiple services to ensure broad access
            health_checks = [
                ('EC2', 'ec2', 'describe_regions'),
                ('IAM', 'iam', 'get_account_summary'),
                ('S3', 's3', 'list_buckets')
            ]
            
            failed_services = []
            for service_name, service_code, test_operation in health_checks:
                try:
                    client = session.client(service_code, region_name='us-east-1')
                    # Light test operation for each service
                    if service_code == 'ec2':
                        client.describe_regions()
                    elif service_code == 'iam':
                        client.get_account_summary()
                    elif service_code == 's3':
                        client.list_buckets()
                    
                    service_details.append(f"✓ {service_name}: Accessible")
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                        permission_issue = f"Limited {service_name} permissions ({error_code})"
                        issues.append(permission_issue)
                        service_details.append(f"⚠ {service_name}: {permission_issue}")
                    else:
                        failed_services.append(service_name)
                        service_details.append(f"✗ {service_name}: Failed ({error_code})")
                except Exception as e:
                    failed_services.append(service_name)
                    service_details.append(f"✗ {service_name}: Error ({str(e)[:50]})")
            
            # Store service details for potential display
            setattr(self, f'_health_details_{profile_name}', service_details)
            
            # Determine health status
            if failed_services:
                issues.append(f"Service access issues: {', '.join(failed_services)}")
                return AccountHealth.ERROR, issues
            elif issues:
                return AccountHealth.WARNING, issues
            else:
                return AccountHealth.HEALTHY, []
                
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            issues.append(error_msg)
            service_details.append(f"✗ Health Check: {error_msg}")
            setattr(self, f'_health_details_{profile_name}', service_details)
            return AccountHealth.ERROR, issues
    
    def get_health_details(self, profile_name: str) -> List[str]:
        """Get detailed health check information for a profile"""
        return getattr(self, f'_health_details_{profile_name}', [])
    
    async def get_account_activity(self, profile_name: str) -> Optional[datetime]:
        """Get last activity timestamp for an account"""
        try:
            session_kwargs = {} if profile_name == 'default' else {'profile_name': profile_name}
            session = aioboto3.Session(**session_kwargs)
            
            # Check CloudTrail for recent activity (if accessible)
            try:
                async with session.client('cloudtrail', region_name='us-east-1') as ct:
                    response = await ct.lookup_events(
                        LookupAttributes=[
                            {
                                'AttributeKey': 'EventName',
                                'AttributeValue': 'ConsoleLogin'  # Any console login
                            }
                        ],
                        StartTime=datetime.utcnow() - timedelta(days=30),
                        MaxItems=1
                    )
                    
                    events = response.get('Events', [])
                    if events:
                        return events[0]['EventTime']
            except:
                pass  # CloudTrail might not be accessible
            
            # Fallback: Check EC2 instances for recent launches
            try:
                async with session.client('ec2', region_name='us-east-1') as ec2:
                    response = await ec2.describe_instances(
                        Filters=[
                            {
                                'Name': 'instance-state-name',
                                'Values': ['running', 'stopped']
                            }
                        ],
                        MaxResults=5
                    )
                    
                    latest_launch = None
                    for reservation in response.get('Reservations', []):
                        for instance in reservation.get('Instances', []):
                            launch_time = instance.get('LaunchTime')
                            if launch_time and (not latest_launch or launch_time > latest_launch):
                                latest_launch = launch_time
                    
                    return latest_launch
            except:
                pass
            
            return None
            
        except Exception:
            return None
    
    async def get_account_resource_count(self, profile_name: str) -> int:
        """Get approximate resource count for an account"""
        try:
            session_kwargs = {} if profile_name == 'default' else {'profile_name': profile_name}
            session = aioboto3.Session(**session_kwargs)
            
            resource_count = 0
            
            # Count key resources
            try:
                async with session.client('ec2', region_name='us-east-1') as ec2:
                    # Count EC2 instances
                    response = await ec2.describe_instances()
                    for reservation in response.get('Reservations', []):
                        resource_count += len(reservation.get('Instances', []))
                    
                    # Count other EC2 resources
                    vpcs = await ec2.describe_vpcs()
                    resource_count += len(vpcs.get('Vpcs', []))
                    
                    sgs = await ec2.describe_security_groups()
                    resource_count += len(sgs.get('SecurityGroups', []))
            except:
                pass
            
            try:
                async with session.client('s3', region_name='us-east-1') as s3:
                    response = await s3.list_buckets()
                    resource_count += len(response.get('Buckets', []))
            except:
                pass
            
            try:
                async with session.client('iam', region_name='us-east-1') as iam:
                    users = await iam.list_users()
                    resource_count += len(users.get('Users', []))
                    
                    roles = await iam.list_roles()
                    resource_count += len(roles.get('Roles', []))
            except:
                pass
            
            return resource_count
            
        except Exception:
            return 0
    
    def load_nicknames(self) -> Dict[str, str]:
        """Load account nicknames from cache"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    return cache.get('nicknames', {})
        except:
            pass
        return {}
    
    def save_nickname(self, profile_name: str, nickname: str):
        """Save account nickname to cache"""
        try:
            cache = {}
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            
            if 'nicknames' not in cache:
                cache['nicknames'] = {}
            
            cache['nicknames'][profile_name] = nickname
            cache['updated'] = datetime.utcnow().isoformat()
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
                
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save nickname: {e}[/yellow]")
    
    async def get_enhanced_accounts(self, include_health_check: bool = True) -> List[AccountProfile]:
        """Get enhanced account profiles with intelligence"""
        from ..aws import aws_session
        
        # Get basic account info
        profiles = aws_session.multi_account.discover_profiles()
        accounts = await aws_session.multi_account.discover_accounts()
        
        # Load cached nicknames
        nicknames = self.load_nicknames()
        
        enhanced_accounts = []
        
        for account in accounts:
            profile_name = account['profile']
            account_id = account['account_id']
            
            # Categorize account
            category = self.categorize_account(
                profile_name, 
                account_id, 
                account.get('description', '')
            )
            
            # Health check (optional for performance)
            if include_health_check:
                health, health_issues = await self.check_account_health(profile_name)
            else:
                health = AccountHealth.UNKNOWN
            
            # Enhanced profile
            profile = AccountProfile(
                name=profile_name,
                account_id=account_id,
                type=account.get('type', 'unknown'),
                region=account.get('region', 'us-east-1'),
                status='active' if profile_name in [acc['profile'] for acc in accounts] else 'inactive',
                category=category,
                health=health,
                nickname=nicknames.get(profile_name),
                description=account.get('description', f"Profile: {profile_name}"),
                tags={'environment': category.value}
            )
            
            enhanced_accounts.append(profile)
        
        return enhanced_accounts
    
    def create_enhanced_accounts_table(self, accounts: List[AccountProfile]) -> Table:
        """Create enhanced accounts table with intelligence"""
        table = Table(title="AWS Accounts & Profiles", show_header=True, header_style="bold magenta")
        
        # Dynamic columns based on available data
        table.add_column("Name", style="cyan", min_width=15)
        table.add_column("Nickname", style="blue", min_width=12)
        table.add_column("Category", style="green", min_width=12)
        table.add_column("Account ID", style="yellow", min_width=14)
        table.add_column("Health", style="white", min_width=8)
        table.add_column("Type", style="magenta", min_width=10)
        table.add_column("Description", min_width=25)
        
        # Sort accounts: production first, then by category, then by name
        def sort_key(acc):
            category_priority = {
                AccountCategory.PRODUCTION: 1,
                AccountCategory.STAGING: 2,
                AccountCategory.DEVELOPMENT: 3,
                AccountCategory.SECURITY: 4,
                AccountCategory.SHARED_SERVICES: 5,
                AccountCategory.SANDBOX: 6,
                AccountCategory.BACKUP: 7,
                AccountCategory.LOGGING: 8,
                AccountCategory.UNKNOWN: 9
            }
            return (category_priority.get(acc.category, 99), acc.name)
        
        sorted_accounts = sorted(accounts, key=sort_key)
        
        for account in sorted_accounts:
            # Format health status with colors
            health_display = account.health.value
            if account.health == AccountHealth.HEALTHY:
                health_display = f"[green]✓ {health_display}[/green]"
            elif account.health == AccountHealth.WARNING:
                health_display = f"[yellow]⚠ {health_display}[/yellow]"
            elif account.health == AccountHealth.ERROR:
                health_display = f"[red]✗ {health_display}[/red]"
            else:
                health_display = f"[dim]? {health_display}[/dim]"
            
            # Format category with colors
            category_display = account.category.value
            if account.category == AccountCategory.PRODUCTION:
                category_display = f"[red bold]{category_display}[/red bold]"
            elif account.category == AccountCategory.STAGING:
                category_display = f"[yellow]{category_display}[/yellow]"
            elif account.category == AccountCategory.DEVELOPMENT:
                category_display = f"[green]{category_display}[/green]"
            elif account.category == AccountCategory.SECURITY:
                category_display = f"[blue]{category_display}[/blue]"
            
            table.add_row(
                account.name,
                account.nickname or "[dim]—[/dim]",
                category_display,
                account.account_id,
                health_display,
                account.type.title(),
                account.description
            )
        
        return table
    
    def get_accounts_by_category(self, accounts: List[AccountProfile]) -> Dict[AccountCategory, List[AccountProfile]]:
        """Group accounts by category"""
        categorized = {}
        for account in accounts:
            if account.category not in categorized:
                categorized[account.category] = []
            categorized[account.category].append(account)
        return categorized


# Global instance
account_intelligence = AccountIntelligence() 