"""AWS Security Audit Service"""

import asyncio
from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.console import Console
from rich import print as rprint

import aioboto3
import boto3


class SecurityFinding:
    """Represents a security finding"""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        finding_type: str,
        severity: str,
        description: str,
        region: str,
        account: str = None,
        remediation: str = None
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.finding_type = finding_type
        self.severity = severity  # HIGH, MEDIUM, LOW
        self.description = description
        self.region = region
        self.account = account
        self.remediation = remediation


async def audit_s3_buckets(regions: List[str] = None, all_regions: bool = True) -> List[SecurityFinding]:
    """Audit S3 buckets for security misconfigurations"""
    findings = []
    
    try:
        # S3 is global, but we'll check from us-east-1
        region = 'us-east-1'
        session = aioboto3.Session()
        
        async with session.client('s3', region_name=region) as s3_client:
            # List all buckets
            response = await s3_client.list_buckets()
            buckets = response.get('Buckets', [])
            
            for bucket in buckets:
                bucket_name = bucket['Name']
                
                try:
                    # Check if bucket is publicly readable
                    try:
                        acl = await s3_client.get_bucket_acl(Bucket=bucket_name)
                        for grant in acl.get('Grants', []):
                            grantee = grant.get('Grantee', {})
                            
                            # Check for public read access
                            if (grantee.get('Type') == 'Group' and 
                                grantee.get('URI') in [
                                    'http://acs.amazonaws.com/groups/global/AllUsers',
                                    'http://acs.amazonaws.com/groups/global/AuthenticatedUsers'
                                ]):
                                
                                permission = grant.get('Permission')
                                if permission in ['READ', 'FULL_CONTROL']:
                                    findings.append(SecurityFinding(
                                        resource_type='S3',
                                        resource_id=bucket_name,
                                        finding_type='PUBLIC_BUCKET',
                                        severity='HIGH',
                                        description=f'Bucket allows public {permission.lower()} access',
                                        region=region,
                                        remediation='Remove public ACL permissions'
                                    ))
                    
                    except Exception as e:
                        # Access denied or other error - skip this bucket
                        continue
                        
                    # Check bucket policy for public access
                    try:
                        policy_response = await s3_client.get_bucket_policy(Bucket=bucket_name)
                        policy = policy_response.get('Policy', '')
                        
                        # Simple check for wildcard principals
                        if '"Principal": "*"' in policy or '"Principal":"*"' in policy:
                            findings.append(SecurityFinding(
                                resource_type='S3',
                                resource_id=bucket_name,
                                finding_type='PUBLIC_POLICY',
                                severity='HIGH',
                                description='Bucket policy allows public access via wildcard principal',
                                region=region,
                                remediation='Review and restrict bucket policy'
                            ))
                            
                    except Exception:
                        # No policy or access denied - continue
                        pass
                        
                    # Check encryption
                    try:
                        encryption = await s3_client.get_bucket_encryption(Bucket=bucket_name)
                    except Exception:
                        # No encryption configured
                        findings.append(SecurityFinding(
                            resource_type='S3',
                            resource_id=bucket_name,
                            finding_type='NO_ENCRYPTION',
                            severity='MEDIUM',
                            description='Bucket does not have server-side encryption enabled',
                            region=region,
                            remediation='Enable S3 server-side encryption'
                        ))
                        
                except Exception as e:
                    # Skip buckets we can't access
                    continue
                
    except Exception as e:
        rprint(f"[red]Error auditing S3 buckets: {e}[/red]")
    
    return findings


async def audit_iam_users() -> List[SecurityFinding]:
    """Audit IAM users for security issues"""
    findings = []
    
    try:
        session = aioboto3.Session()
        
        async with session.client('iam', region_name='us-east-1') as iam_client:  # IAM is global
            # List all users
            paginator = iam_client.get_paginator('list_users')
            
            async for page in paginator.paginate():
                users = page.get('Users', [])
                
                for user in users:
                    username = user['UserName']
                    user_creation_date = user.get('CreateDate')
                    
                    # Check for users with admin policies
                    try:
                        attached_policies = await iam_client.list_attached_user_policies(UserName=username)
                        for policy in attached_policies.get('AttachedPolicies', []):
                            if 'Administrator' in policy['PolicyName'] or policy['PolicyArn'].endswith('AdministratorAccess'):
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=username,
                                    finding_type='ADMIN_USER',
                                    severity='HIGH',
                                    description='User has administrator access policy attached',
                                    region='global',
                                    remediation='Use roles instead of users for admin access'
                                ))
                    except Exception:
                        continue
                        
                    # Check for inline policies with admin permissions
                    try:
                        inline_policies = await iam_client.list_user_policies(UserName=username)
                        for policy_name in inline_policies.get('PolicyNames', []):
                            policy_doc = await iam_client.get_user_policy(UserName=username, PolicyName=policy_name)
                            policy_content = str(policy_doc.get('PolicyDocument', {}))
                            
                            if '"Effect": "Allow"' in policy_content and '"Action": "*"' in policy_content:
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=username,
                                    finding_type='ADMIN_INLINE_POLICY',
                                    severity='HIGH',
                                    description=f'User has inline policy with wildcard permissions: {policy_name}',
                                    region='global',
                                    remediation='Replace inline policies with managed policies'
                                ))
                    except Exception:
                        continue
                    
                    # NEW: Check MFA status
                    try:
                        mfa_devices = await iam_client.list_mfa_devices(UserName=username)
                        if not mfa_devices.get('MFADevices', []):
                            findings.append(SecurityFinding(
                                resource_type='IAM',
                                resource_id=username,
                                finding_type='NO_MFA',
                                severity='MEDIUM',
                                description='User does not have MFA enabled',
                                region='global',
                                remediation='Enable MFA for this user account'
                            ))
                    except Exception:
                        continue
                    
                    # NEW: Check access key age and status
                    try:
                        access_keys = await iam_client.list_access_keys(UserName=username)
                        for key_info in access_keys.get('AccessKeyMetadata', []):
                            key_id = key_info['AccessKeyId']
                            key_status = key_info['Status']
                            key_creation_date = key_info.get('CreateDate')
                            
                            if key_status == 'Active' and key_creation_date:
                                # Calculate key age in days
                                from datetime import datetime, timezone
                                import pytz
                                
                                if isinstance(key_creation_date, str):
                                    key_creation_date = datetime.fromisoformat(key_creation_date.replace('Z', '+00:00'))
                                elif not key_creation_date.tzinfo:
                                    key_creation_date = key_creation_date.replace(tzinfo=timezone.utc)
                                
                                now = datetime.now(timezone.utc)
                                key_age_days = (now - key_creation_date).days
                                
                                if key_age_days > 90:
                                    findings.append(SecurityFinding(
                                        resource_type='IAM',
                                        resource_id=f'{username}:{key_id[-4:]}',  # Show last 4 chars of key
                                        finding_type='OLD_ACCESS_KEY',
                                        severity='MEDIUM',
                                        description=f'Access key is {key_age_days} days old (>90 days)',
                                        region='global',
                                        remediation='Rotate access keys regularly (every 90 days)'
                                    ))
                                elif key_age_days > 365:
                                    findings.append(SecurityFinding(
                                        resource_type='IAM',
                                        resource_id=f'{username}:{key_id[-4:]}',
                                        finding_type='VERY_OLD_ACCESS_KEY',
                                        severity='HIGH',
                                        description=f'Access key is {key_age_days} days old (>365 days)',
                                        region='global',
                                        remediation='Immediately rotate this very old access key'
                                    ))
                    except Exception:
                        continue
                    
                    # NEW: Check for unused users (no activity in 90+ days)
                    try:
                        # Check password last used
                        password_last_used = user.get('PasswordLastUsed')
                        if password_last_used:
                            if isinstance(password_last_used, str):
                                password_last_used = datetime.fromisoformat(password_last_used.replace('Z', '+00:00'))
                            elif not password_last_used.tzinfo:
                                password_last_used = password_last_used.replace(tzinfo=timezone.utc)
                            
                            now = datetime.now(timezone.utc)
                            days_since_password_use = (now - password_last_used).days
                            
                            if days_since_password_use > 90:
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=username,
                                    finding_type='INACTIVE_USER',
                                    severity='LOW',
                                    description=f'User has not used password in {days_since_password_use} days',
                                    region='global',
                                    remediation='Review if user account is still needed'
                                ))
                        
                        # For programmatic users (no password), check if they have old access keys
                        elif not user.get('LoginProfile'):  # No console access
                            access_keys = await iam_client.list_access_keys(UserName=username)
                            if access_keys.get('AccessKeyMetadata'):
                                # User has access keys but no console access - programmatic user
                                # Check if any recent activity via access keys (we'd need CloudTrail for this)
                                # For now, just flag if user was created long ago and has old keys
                                if user_creation_date:
                                    if isinstance(user_creation_date, str):
                                        user_creation_date = datetime.fromisoformat(user_creation_date.replace('Z', '+00:00'))
                                    elif not user_creation_date.tzinfo:
                                        user_creation_date = user_creation_date.replace(tzinfo=timezone.utc)
                                    
                                    now = datetime.now(timezone.utc)
                                    days_since_creation = (now - user_creation_date).days
                                    
                                    if days_since_creation > 180:  # 6 months old
                                        findings.append(SecurityFinding(
                                            resource_type='IAM',
                                            resource_id=username,
                                            finding_type='OLD_PROGRAMMATIC_USER',
                                            severity='LOW',
                                            description=f'Programmatic user created {days_since_creation} days ago - verify still needed',
                                            region='global',
                                            remediation='Review if programmatic user is still actively used'
                                        ))
                    except Exception:
                        continue
                        
    except Exception as e:
        rprint(f"[red]Error auditing IAM users: {e}[/red]")
    
    return findings


async def audit_iam_policies() -> List[SecurityFinding]:
    """Audit IAM policies for overly permissive configurations"""
    findings = []
    
    try:
        session = aioboto3.Session()
        
        async with session.client('iam', region_name='us-east-1') as iam_client:
            # Check customer managed policies
            paginator = iam_client.get_paginator('list_policies')
            
            async for page in paginator.paginate(Scope='Local'):  # Customer managed policies only
                policies = page.get('Policies', [])
                
                for policy in policies:
                    policy_name = policy['PolicyName']
                    policy_arn = policy['Arn']
                    
                    try:
                        # Get the default version of the policy
                        policy_version = await iam_client.get_policy_version(
                            PolicyArn=policy_arn,
                            VersionId=policy['DefaultVersionId']
                        )
                        
                        policy_document = policy_version['PolicyVersion']['Document']
                        policy_content = str(policy_document)
                        
                        # Check for wildcard permissions
                        if '"Action": "*"' in policy_content and '"Effect": "Allow"' in policy_content:
                            # Check if it's scoped to specific resources
                            if '"Resource": "*"' in policy_content:
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=policy_name,
                                    finding_type='WILDCARD_POLICY',
                                    severity='HIGH',
                                    description='Policy grants wildcard permissions (*) on all resources (*)',
                                    region='global',
                                    remediation='Scope policy to specific actions and resources'
                                ))
                            else:
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=policy_name,
                                    finding_type='BROAD_POLICY',
                                    severity='MEDIUM',
                                    description='Policy grants wildcard actions (*) but with scoped resources',
                                    region='global',
                                    remediation='Limit policy to specific actions needed'
                                ))
                                
                        # Check for specific high-risk permissions
                        high_risk_actions = [
                            'iam:*',
                            'sts:AssumeRole', 
                            'ec2:*',
                            's3:*',
                            'rds:*'
                        ]
                        
                        for risk_action in high_risk_actions:
                            if f'"{risk_action}"' in policy_content and '"Effect": "Allow"' in policy_content:
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=policy_name,
                                    finding_type='HIGH_RISK_PERMISSION',
                                    severity='MEDIUM',
                                    description=f'Policy contains high-risk permission: {risk_action}',
                                    region='global',
                                    remediation=f'Review necessity of {risk_action} permission'
                                ))
                                
                    except Exception:
                        continue
                        
    except Exception as e:
        rprint(f"[red]Error auditing IAM policies: {e}[/red]")
    
    return findings


def create_audit_table(findings: List[SecurityFinding], show_account: bool = False) -> Table:
    """Create a Rich table for security findings"""
    table = Table(title="Security Audit Results")
    
    if show_account:
        table.add_column("Account", style="cyan", no_wrap=True, width=12)
    table.add_column("Severity", style="bold", no_wrap=True, width=8)
    table.add_column("Service", style="blue", no_wrap=True, width=7) 
    table.add_column("Resource", style="green", no_wrap=True, width=40)
    table.add_column("Finding", style="yellow", no_wrap=True, width=15)
    table.add_column("Description", style="white", width=50)
    table.add_column("Region", style="dim", no_wrap=True, width=10)
    
    # Sort by severity (HIGH first, then MEDIUM, then LOW)
    severity_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    sorted_findings = sorted(findings, key=lambda x: severity_order.get(x.severity, 3))
    
    for finding in sorted_findings:
        # Color code severity
        if finding.severity == 'HIGH':
            severity_display = f"[red]{finding.severity}[/red]"
        elif finding.severity == 'MEDIUM':
            severity_display = f"[yellow]{finding.severity}[/yellow]"
        else:
            severity_display = f"[green]{finding.severity}[/green]"
        
        row = []
        if show_account:
            row.append(finding.account or 'current')
        
        row.extend([
            severity_display,
            finding.resource_type,
            finding.resource_id,
            finding.finding_type,
            finding.description,
            finding.region
        ])
        
        table.add_row(*row)
    
    return table


async def run_security_audit(
    services: List[str] = None,
    regions: List[str] = None,
    all_regions: bool = True,
    profiles: List[str] = None
) -> List[SecurityFinding]:
    """Run comprehensive security audit"""
    
    all_findings = []
    
    if not services:
        services = ['s3', 'iam']  # Default services to audit
    
    console = Console()
    
    with console.status("[bold green]Running security audit...", spinner="dots"):
        # Run S3 audit if requested
        if 's3' in services:
            console.print("[dim]Auditing S3 buckets...[/dim]")
            s3_findings = await audit_s3_buckets(regions, all_regions)
            all_findings.extend(s3_findings)
            
        # Run IAM audit if requested
        if 'iam' in services:
            console.print("[dim]Auditing IAM users...[/dim]")
            iam_user_findings = await audit_iam_users()
            all_findings.extend(iam_user_findings)
            
            console.print("[dim]Auditing IAM policies...[/dim]")
            iam_policy_findings = await audit_iam_policies()
            all_findings.extend(iam_policy_findings)
    
    return all_findings


def get_security_summary(findings: List[SecurityFinding]) -> Dict[str, Any]:
    """Generate security summary statistics"""
    if not findings:
        return {
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {},
            'score': 100
        }
    
    high_count = sum(1 for f in findings if f.severity == 'HIGH')
    medium_count = sum(1 for f in findings if f.severity == 'MEDIUM')
    low_count = sum(1 for f in findings if f.severity == 'LOW')
    
    # Count by service
    services = {}
    for finding in findings:
        services[finding.resource_type] = services.get(finding.resource_type, 0) + 1
    
    # Simple scoring: start at 100, subtract points for findings
    score = 100
    score -= (high_count * 20)    # High findings: -20 points each
    score -= (medium_count * 10)  # Medium findings: -10 points each  
    score -= (low_count * 5)      # Low findings: -5 points each
    score = max(0, score)         # Don't go below 0
    
    return {
        'total': len(findings),
        'high': high_count,
        'medium': medium_count,
        'low': low_count,
        'services': services,
        'score': score
    } 