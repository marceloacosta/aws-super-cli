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


async def audit_s3_buckets(regions: List[str] = None, all_regions: bool = True, account: str = None) -> List[SecurityFinding]:
    """Audit S3 buckets for security misconfigurations - Phase 3 comprehensive assessment"""
    findings = []
    
    try:
        # S3 is global, but we'll check from us-east-1
        region = 'us-east-1'
        
        # Create session with the provided account/profile
        if account:
            session = aioboto3.Session(profile_name=account)
        else:
            session = aioboto3.Session()
        
        async with session.client('s3', region_name=region) as s3_client:
            # First, check account-level public access block configuration
            try:
                account_pab = await s3_client.get_public_access_block()
                pab_config = account_pab.get('PublicAccessBlockConfiguration', {})
                
                if not all([
                    pab_config.get('BlockPublicAcls', False),
                    pab_config.get('IgnorePublicAcls', False),
                    pab_config.get('BlockPublicPolicy', False),
                    pab_config.get('RestrictPublicBuckets', False)
                ]):
                    findings.append(SecurityFinding(
                        resource_type='S3',
                        resource_id='Account-Level',
                        finding_type='ACCOUNT_PUBLIC_ACCESS_BLOCK',
                        severity='HIGH',
                        description='Account-level public access block is not fully configured',
                        region=region,
                        remediation='Enable all account-level public access block settings',
                        account=account
                    ))
            except Exception:
                # No account-level public access block configured
                findings.append(SecurityFinding(
                    resource_type='S3',
                    resource_id='Account-Level',
                    finding_type='NO_ACCOUNT_PUBLIC_ACCESS_BLOCK',
                    severity='HIGH',
                    description='Account-level public access block is not configured',
                    region=region,
                    remediation='Configure account-level public access block settings',
                    account=account
                ))
            
            # List all buckets
            response = await s3_client.list_buckets()
            buckets = response.get('Buckets', [])
            
            for bucket in buckets:
                bucket_name = bucket['Name']
                
                try:
                    # Get bucket location to handle region-specific calls
                    try:
                        location_response = await s3_client.get_bucket_location(Bucket=bucket_name)
                        bucket_region = location_response.get('LocationConstraint') or 'us-east-1'
                        if bucket_region == 'EU':
                            bucket_region = 'eu-west-1'
                    except Exception:
                        bucket_region = 'us-east-1'
                    
                    # Create region-specific client for this bucket
                    async with session.client('s3', region_name=bucket_region) as bucket_s3_client:
                        
                        # Check bucket-level public access block
                        try:
                            bucket_pab = await bucket_s3_client.get_public_access_block(Bucket=bucket_name)
                            pab_config = bucket_pab.get('PublicAccessBlockConfiguration', {})
                            
                            if not all([
                                pab_config.get('BlockPublicAcls', False),
                                pab_config.get('IgnorePublicAcls', False),
                                pab_config.get('BlockPublicPolicy', False),
                                pab_config.get('RestrictPublicBuckets', False)
                            ]):
                                findings.append(SecurityFinding(
                                    resource_type='S3',
                                    resource_id=bucket_name,
                                    finding_type='BUCKET_PUBLIC_ACCESS_BLOCK',
                                    severity='MEDIUM',
                                    description='Bucket public access block is not fully configured',
                                    region=bucket_region,
                                    remediation='Enable all bucket-level public access block settings',
                                    account=account
                                ))
                        except Exception:
                            # No bucket-level public access block configured
                            findings.append(SecurityFinding(
                                resource_type='S3',
                                resource_id=bucket_name,
                                finding_type='NO_BUCKET_PUBLIC_ACCESS_BLOCK',
                                severity='MEDIUM',
                                description='Bucket public access block is not configured',
                                region=bucket_region,
                                remediation='Configure bucket-level public access block settings',
                                account=account
                            ))
                        
                        # Check versioning status
                        try:
                            versioning = await bucket_s3_client.get_bucket_versioning(Bucket=bucket_name)
                            versioning_status = versioning.get('Status', 'Off')
                            mfa_delete = versioning.get('MfaDelete', 'Disabled')
                            
                            if versioning_status != 'Enabled':
                                findings.append(SecurityFinding(
                                    resource_type='S3',
                                    resource_id=bucket_name,
                                    finding_type='VERSIONING_DISABLED',
                                    severity='MEDIUM',
                                    description='Bucket versioning is not enabled - data protection risk',
                                    region=bucket_region,
                                    remediation='Enable S3 bucket versioning for data protection',
                                    account=account
                                ))
                            
                            if versioning_status == 'Enabled' and mfa_delete != 'Enabled':
                                findings.append(SecurityFinding(
                                    resource_type='S3',
                                    resource_id=bucket_name,
                                    finding_type='MFA_DELETE_DISABLED',
                                    severity='LOW',
                                    description='MFA delete is not enabled for versioned bucket',
                                    region=bucket_region,
                                    remediation='Consider enabling MFA delete for additional protection',
                                    account=account
                                ))
                        except Exception:
                            continue
                        
                        # Check lifecycle policies
                        try:
                            lifecycle = await bucket_s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                            # Lifecycle is configured - good for cost optimization
                        except Exception:
                            # No lifecycle policy configured
                            findings.append(SecurityFinding(
                                resource_type='S3',
                                resource_id=bucket_name,
                                finding_type='NO_LIFECYCLE_POLICY',
                                severity='LOW',
                                description='No lifecycle policy configured - potential cost optimization missed',
                                region=bucket_region,
                                remediation='Configure lifecycle policy to optimize storage costs',
                                account=account
                            ))
                        
                        # Enhanced encryption analysis
                        try:
                            encryption = await bucket_s3_client.get_bucket_encryption(Bucket=bucket_name)
                            encryption_config = encryption.get('ServerSideEncryptionConfiguration', {})
                            rules = encryption_config.get('Rules', [])
                            
                            if rules:
                                for rule in rules:
                                    sse_config = rule.get('ApplyServerSideEncryptionByDefault', {})
                                    sse_algorithm = sse_config.get('SSEAlgorithm', '')
                                    kms_key_id = sse_config.get('KMSMasterKeyID', '')
                                    
                                    if sse_algorithm == 'AES256':
                                        findings.append(SecurityFinding(
                                            resource_type='S3',
                                            resource_id=bucket_name,
                                            finding_type='S3_MANAGED_ENCRYPTION',
                                            severity='LOW',
                                            description='Using S3-managed encryption (AES256) instead of KMS',
                                            region=bucket_region,
                                            remediation='Consider upgrading to KMS encryption for better key management',
                                            account=account
                                        ))
                                    elif sse_algorithm == 'aws:kms':
                                        if not kms_key_id or kms_key_id.startswith('arn:aws:kms'):
                                            # Using customer-managed KMS key - good!
                                            pass
                                        else:
                                            # Using AWS managed key
                                            findings.append(SecurityFinding(
                                                resource_type='S3',
                                                resource_id=bucket_name,
                                                finding_type='AWS_MANAGED_KMS_KEY',
                                                severity='LOW',
                                                description='Using AWS-managed KMS key instead of customer-managed key',
                                                region=bucket_region,
                                                remediation='Consider using customer-managed KMS key for better control',
                                                account=account
                                            ))
                        except Exception:
                            # No encryption configured - already handled in original code
                            findings.append(SecurityFinding(
                                resource_type='S3',
                                resource_id=bucket_name,
                                finding_type='NO_ENCRYPTION',
                                severity='HIGH',
                                description='Bucket does not have server-side encryption enabled',
                                region=bucket_region,
                                remediation='Enable S3 server-side encryption with KMS',
                                account=account
                            ))
                        
                        # Check access logging
                        try:
                            logging_config = await bucket_s3_client.get_bucket_logging(Bucket=bucket_name)
                            if not logging_config.get('LoggingEnabled'):
                                findings.append(SecurityFinding(
                                    resource_type='S3',
                                    resource_id=bucket_name,
                                    finding_type='NO_ACCESS_LOGGING',
                                    severity='MEDIUM',
                                    description='Bucket access logging is not enabled',
                                    region=bucket_region,
                                    remediation='Enable S3 access logging for audit trail',
                                    account=account
                                ))
                        except Exception:
                            # No logging configured
                            findings.append(SecurityFinding(
                                resource_type='S3',
                                resource_id=bucket_name,
                                finding_type='NO_ACCESS_LOGGING',
                                severity='MEDIUM',
                                description='Bucket access logging is not enabled',
                                region=bucket_region,
                                remediation='Enable S3 access logging for audit trail',
                                account=account
                            ))
                        
                        # Enhanced ACL analysis - existing code
                        try:
                            acl = await bucket_s3_client.get_bucket_acl(Bucket=bucket_name)
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
                                            finding_type='PUBLIC_ACL',
                                            severity='HIGH',
                                            description=f'Bucket ACL allows public {permission.lower()} access',
                                            region=bucket_region,
                                            remediation='Remove public ACL permissions',
                                            account=account
                                        ))
                                    elif permission in ['WRITE', 'WRITE_ACP']:
                                        findings.append(SecurityFinding(
                                            resource_type='S3',
                                            resource_id=bucket_name,
                                            finding_type='PUBLIC_WRITE_ACL',
                                            severity='HIGH',
                                            description=f'Bucket ACL allows public {permission.lower()} access',
                                            region=bucket_region,
                                            remediation='Remove public write ACL permissions immediately',
                                            account=account
                                        ))
                        except Exception:
                            continue
                            
                        # Enhanced bucket policy check - existing code  
                        try:
                            policy_response = await bucket_s3_client.get_bucket_policy(Bucket=bucket_name)
                            policy = policy_response.get('Policy', '')
                            
                            # Enhanced wildcard principal check
                            if '"Principal": "*"' in policy or '"Principal":"*"' in policy:
                                findings.append(SecurityFinding(
                                    resource_type='S3',
                                    resource_id=bucket_name,
                                    finding_type='PUBLIC_POLICY',
                                    severity='HIGH',
                                    description='Bucket policy allows public access via wildcard principal',
                                    region=bucket_region,
                                    remediation='Review and restrict bucket policy to specific principals',
                                    account=account
                                ))
                            
                            # Check for unsecured transport
                            if '"aws:SecureTransport": "false"' not in policy.lower():
                                findings.append(SecurityFinding(
                                    resource_type='S3',
                                    resource_id=bucket_name,
                                    finding_type='INSECURE_TRANSPORT_ALLOWED',
                                    severity='MEDIUM',
                                    description='Bucket policy does not enforce HTTPS/TLS',
                                    region=bucket_region,
                                    remediation='Add policy condition to deny requests without SecureTransport',
                                    account=account
                                ))
                                
                        except Exception:
                            # No policy or access denied - continue
                            pass
                            
                except Exception as e:
                    # Skip buckets we can't access
                    continue
                
    except Exception as e:
        rprint(f"[red]Error auditing S3 buckets: {e}[/red]")
    
    return findings


async def audit_iam_users(account: str = None) -> List[SecurityFinding]:
    """Audit IAM users for security issues"""
    findings = []
    
    try:
        # Create session with the provided account/profile
        if account:
            session = aioboto3.Session(profile_name=account)
        else:
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
                                    remediation='Use roles instead of users for admin access',
                                    account=account
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
                                    remediation='Replace inline policies with managed policies',
                                    account=account
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
                                remediation='Enable MFA for this user account',
                                account=account
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
                                        remediation='Rotate access keys regularly (every 90 days)',
                                        account=account
                                    ))
                                elif key_age_days > 365:
                                    findings.append(SecurityFinding(
                                        resource_type='IAM',
                                        resource_id=f'{username}:{key_id[-4:]}',
                                        finding_type='VERY_OLD_ACCESS_KEY',
                                        severity='HIGH',
                                        description=f'Access key is {key_age_days} days old (>365 days)',
                                        region='global',
                                        remediation='Immediately rotate this very old access key',
                                        account=account
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
                                    remediation='Review if user account is still needed',
                                    account=account
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
                                            remediation='Review if programmatic user is still actively used',
                                            account=account
                                        ))
                    except Exception:
                        continue
                        
    except Exception as e:
        rprint(f"[red]Error auditing IAM users: {e}[/red]")
    
    return findings


async def audit_iam_policies(account: str = None) -> List[SecurityFinding]:
    """Audit IAM policies for overly permissive configurations"""
    findings = []
    
    try:
        # Create session with the provided account/profile
        if account:
            session = aioboto3.Session(profile_name=account)
        else:
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
                                    remediation='Scope policy to specific actions and resources',
                                    account=account
                                ))
                            else:
                                findings.append(SecurityFinding(
                                    resource_type='IAM',
                                    resource_id=policy_name,
                                    finding_type='BROAD_POLICY',
                                    severity='MEDIUM',
                                    description='Policy grants wildcard actions (*) but with scoped resources',
                                    region='global',
                                    remediation='Limit policy to specific actions needed',
                                    account=account
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
                                    remediation=f'Review necessity of {risk_action} permission',
                                    account=account
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
        services = ['s3', 'iam', 'network', 'compute']  # Default services to audit
    
    console = Console()
    
    # Determine which profiles to audit
    if profiles is None:
        # Single account mode - use current profile
        profiles_to_audit = [None]  # None means current profile
        console.print("[dim]Running security audit on current account...[/dim]")
    else:
        # Multi-account mode
        profiles_to_audit = profiles
        console.print(f"[dim]Running security audit on {len(profiles)} accounts: {', '.join(profiles)}[/dim]")
    
    # Audit each profile
    for profile in profiles_to_audit:
        profile_display = profile or "current"
        
        if len(profiles_to_audit) > 1:
            console.print(f"[dim]Auditing account: {profile_display}...[/dim]")
        
        with console.status(f"[bold green]Running security audit on {profile_display}...", spinner="dots"):
            # Run S3 audit if requested
            if 's3' in services:
                console.print(f"[dim]Auditing S3 buckets in {profile_display}...[/dim]")
                s3_findings = await audit_s3_buckets(regions, all_regions, profile)
                # Add profile info to findings
                for finding in s3_findings:
                    if profile:
                        finding.account = profile
                all_findings.extend(s3_findings)
                
            # Run IAM audit if requested
            if 'iam' in services:
                console.print(f"[dim]Auditing IAM users in {profile_display}...[/dim]")
                iam_user_findings = await audit_iam_users(profile)
                # Add profile info to findings
                for finding in iam_user_findings:
                    if profile:
                        finding.account = profile
                all_findings.extend(iam_user_findings)
                
                console.print(f"[dim]Auditing IAM policies in {profile_display}...[/dim]")
                iam_policy_findings = await audit_iam_policies(profile)
                # Add profile info to findings
                for finding in iam_policy_findings:
                    if profile:
                        finding.account = profile
                all_findings.extend(iam_policy_findings)
            
            # Run Network security audit if requested
            if 'network' in services:
                console.print(f"[dim]Auditing network security in {profile_display} (VPCs, Security Groups, NACLs)...[/dim]")
                network_findings = await audit_network_security(regions, all_regions, profile)
                # Add profile info to findings
                for finding in network_findings:
                    if profile:
                        finding.account = profile
                all_findings.extend(network_findings)
            
            # Run Compute security audit if requested
            if 'compute' in services:
                console.print(f"[dim]Auditing compute security in {profile_display} (EC2, Lambda, Containers)...[/dim]")
                compute_findings = await audit_compute_security(regions, all_regions, profile)
                # Add profile info to findings
                for finding in compute_findings:
                    if profile:
                        finding.account = profile
                all_findings.extend(compute_findings)
    
    return all_findings


def get_security_summary(findings: List[SecurityFinding]) -> Dict[str, Any]:
    """Generate security summary statistics with nuanced scoring"""
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
    
    # Enhanced scoring: categorize findings by actual security impact
    score = _calculate_enhanced_security_score(findings)
    
    return {
        'total': len(findings),
        'high': high_count,
        'medium': medium_count,
        'low': low_count,
        'services': services,
        'score': score
    }


def _calculate_enhanced_security_score(findings: List[SecurityFinding]) -> int:
    """
    Calculate security score using weighted categories and logarithmic scaling.
    
    This algorithm addresses the issues with the previous linear approach:
    1. Categorizes findings by actual security impact (not just severity)
    2. Uses logarithmic scaling for diminishing returns
    3. Weights critical security issues more heavily than operational gaps
    4. Provides realistic scores (30-70 range for typical environments)
    """
    import math
    
    # Categorize findings by security impact (not just severity level)
    categories = {
        'critical_exposure': [],      # Public access, open to world
        'encryption_gaps': [],        # Missing encryption, weak crypto
        'access_control': [],         # IAM issues, overprivilege
        'monitoring_gaps': [],        # Missing logs, monitoring
        'operational_cleanup': [],    # Unused resources, old keys
        'configuration_drift': []     # Non-standard configs, best practices
    }
    
    # Categorize each finding based on type, not just severity
    for finding in findings:
        finding_type = finding.finding_type
        
        # Critical Exposure (highest impact)
        if finding_type in [
            'SSH_OPEN_TO_WORLD', 'RDP_OPEN_TO_WORLD', 'ALL_TRAFFIC_OPEN',
            'PUBLIC_ACL', 'PUBLIC_WRITE_ACL', 'PUBLIC_POLICY',
            'PUBLIC_LAMBDA_FUNCTION', 'PUBLIC_INSTANCE_OPEN_ACCESS'
        ]:
            categories['critical_exposure'].append(finding)
            
        # Encryption Gaps (high impact)
        elif finding_type in [
            'NO_ENCRYPTION', 'S3_MANAGED_ENCRYPTION', 'AWS_MANAGED_KMS_KEY',
            'UNENCRYPTED_ENV_VARS', 'INSECURE_TRANSPORT_ALLOWED'
        ]:
            categories['encryption_gaps'].append(finding)
            
        # Access Control Issues (high impact)
        elif finding_type in [
            'ADMIN_USER', 'ADMIN_INLINE_POLICY', 'WILDCARD_POLICY',
            'BROAD_POLICY', 'HIGH_RISK_PERMISSION', 'OVERPRIVILEGED_EXECUTION_ROLE',
            'VERY_OLD_ACCESS_KEY'
        ]:
            categories['access_control'].append(finding)
            
        # Monitoring Gaps (medium impact - important but not immediate vulnerability)
        elif finding_type in [
            'NO_FLOW_LOGS', 'NO_ACCESS_LOGGING', 'NO_DEAD_LETTER_QUEUE',
            'CONTAINER_INSIGHTS_DISABLED'
        ]:
            categories['monitoring_gaps'].append(finding)
            
        # Operational Cleanup (lower impact - housekeeping items)
        elif finding_type in [
            'UNUSED_SECURITY_GROUP', 'OLD_ACCESS_KEY', 'INACTIVE_USER',
            'OLD_PROGRAMMATIC_USER', 'NO_LIFECYCLE_POLICY'
        ]:
            categories['operational_cleanup'].append(finding)
            
        # Configuration Drift (lowest impact - best practices)
        else:
            categories['configuration_drift'].append(finding)
    
    # Calculate weighted score with logarithmic scaling
    base_score = 100
    
    # Critical Exposure: Severe penalty with logarithmic scaling
    critical_count = len(categories['critical_exposure'])
    if critical_count > 0:
        # Heavy penalty: 25 points for first finding, diminishing returns
        critical_penalty = 25 * math.log(critical_count + 1)
        base_score -= min(critical_penalty, 40)  # Cap at 40 points
    
    # Encryption Gaps: Significant penalty with scaling
    encryption_count = len(categories['encryption_gaps'])
    if encryption_count > 0:
        # Moderate penalty: 15 points for first finding, logarithmic scaling
        encryption_penalty = 15 * math.log(encryption_count + 1)
        base_score -= min(encryption_penalty, 25)  # Cap at 25 points
    
    # Access Control: Important but scaled penalty
    access_count = len(categories['access_control'])
    if access_count > 0:
        # Moderate penalty: 12 points for first finding, logarithmic scaling
        access_penalty = 12 * math.log(access_count + 1)
        base_score -= min(access_penalty, 20)  # Cap at 20 points
    
    # Monitoring Gaps: Moderate penalty, heavily scaled
    monitoring_count = len(categories['monitoring_gaps'])
    if monitoring_count > 0:
        # Light penalty: 8 points for first finding, heavy scaling
        monitoring_penalty = 8 * math.log(monitoring_count + 1)
        base_score -= min(monitoring_penalty, 12)  # Cap at 12 points
    
    # Operational Cleanup: Light penalty, very scaled
    operational_count = len(categories['operational_cleanup'])
    if operational_count > 0:
        # Very light penalty: 5 points for first finding, heavy scaling
        operational_penalty = 5 * math.log(operational_count + 1)
        base_score -= min(operational_penalty, 8)  # Cap at 8 points
    
    # Configuration Drift: Minimal penalty
    config_count = len(categories['configuration_drift'])
    if config_count > 0:
        # Minimal penalty: 3 points for first finding, heavy scaling
        config_penalty = 3 * math.log(config_count + 1)
        base_score -= min(config_penalty, 5)  # Cap at 5 points
    
    # Ensure score stays within reasonable bounds
    final_score = max(10, min(100, int(base_score)))
    
    return final_score


async def audit_network_security(regions: List[str] = None, all_regions: bool = True, account: str = None) -> List[SecurityFinding]:
    """Audit network security - VPCs, Security Groups, NACLs, and Subnets"""
    findings = []
    
    if not regions:
        if all_regions:
            # Get all available regions
            session = aioboto3.Session()
            async with session.client('ec2', region_name='us-east-1') as ec2_client:
                regions_response = await ec2_client.describe_regions()
                regions = [region['RegionName'] for region in regions_response['Regions']]
        else:
            regions = ['us-east-1']  # Default region
    
    for region in regions:
        region_findings = await _audit_network_security_region(region, account)
        findings.extend(region_findings)
    
    return findings


async def _audit_network_security_region(region: str, account: str = None) -> List[SecurityFinding]:
    """Audit network security for a specific region"""
    findings = []
    
    try:
        # Create session with the provided account/profile
        if account:
            session = aioboto3.Session(profile_name=account)
        else:
            session = aioboto3.Session()
        
        async with session.client('ec2', region_name=region) as ec2_client:
            # Audit Security Groups
            sg_findings = await _audit_security_groups(ec2_client, region, account)
            findings.extend(sg_findings)
            
            # Audit Network ACLs
            nacl_findings = await _audit_network_acls(ec2_client, region, account)
            findings.extend(nacl_findings)
            
            # Audit VPCs
            vpc_findings = await _audit_vpcs(ec2_client, region, account)
            findings.extend(vpc_findings)
            
            # Audit Subnets
            subnet_findings = await _audit_subnets(ec2_client, region, account)
            findings.extend(subnet_findings)
            
    except Exception as e:
        rprint(f"[red]Error auditing network security in region {region}: {e}[/red]")
    
    return findings


async def _audit_security_groups(ec2_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit Security Groups for overly permissive rules"""
    findings = []
    
    try:
        # Get all security groups
        paginator = ec2_client.get_paginator('describe_security_groups')
        
        async for page in paginator.paginate():
            security_groups = page.get('SecurityGroups', [])
            
            for sg in security_groups:
                sg_id = sg['GroupId']
                sg_name = sg.get('GroupName', 'Unknown')
                vpc_id = sg.get('VpcId', 'Classic')
                
                # Check inbound rules
                for rule in sg.get('IpPermissions', []):
                    protocol = rule.get('IpProtocol', '')
                    from_port = rule.get('FromPort')
                    to_port = rule.get('ToPort')
                    
                    # Check for SSH access from anywhere
                    if (protocol == 'tcp' and 
                        from_port == 22 and to_port == 22):
                        
                        for ip_range in rule.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                findings.append(SecurityFinding(
                                    resource_type='EC2',
                                    resource_id=f"{sg_name} ({sg_id})",
                                    finding_type='SSH_OPEN_TO_WORLD',
                                    severity='HIGH',
                                    description='Security group allows SSH (port 22) from anywhere (0.0.0.0/0)',
                                    region=region,
                                    remediation='Restrict SSH access to specific IP ranges or VPN',
                                    account=account
                                ))
                    
                    # Check for RDP access from anywhere
                    if (protocol == 'tcp' and 
                        from_port == 3389 and to_port == 3389):
                        
                        for ip_range in rule.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                findings.append(SecurityFinding(
                                    resource_type='EC2',
                                    resource_id=f"{sg_name} ({sg_id})",
                                    finding_type='RDP_OPEN_TO_WORLD',
                                    severity='HIGH',
                                    description='Security group allows RDP (port 3389) from anywhere (0.0.0.0/0)',
                                    region=region,
                                    remediation='Restrict RDP access to specific IP ranges or VPN',
                                    account=account
                                ))
                    
                    # Check for all traffic from anywhere
                    if protocol == '-1':  # All protocols
                        for ip_range in rule.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                findings.append(SecurityFinding(
                                    resource_type='EC2',
                                    resource_id=f"{sg_name} ({sg_id})",
                                    finding_type='ALL_TRAFFIC_OPEN',
                                    severity='HIGH',
                                    description='Security group allows all traffic from anywhere (0.0.0.0/0)',
                                    region=region,
                                    remediation='Restrict to specific protocols and ports needed',
                                    account=account
                                ))
                    
                    # Check for wide port ranges from anywhere
                    if (protocol == 'tcp' and from_port is not None and to_port is not None):
                        port_range = to_port - from_port + 1
                        if port_range > 100:  # Arbitrary threshold for "wide"
                            for ip_range in rule.get('IpRanges', []):
                                if ip_range.get('CidrIp') == '0.0.0.0/0':
                                    findings.append(SecurityFinding(
                                        resource_type='EC2',
                                        resource_id=f"{sg_name} ({sg_id})",
                                        finding_type='WIDE_PORT_RANGE',
                                        severity='MEDIUM',
                                        description=f'Security group allows wide port range ({from_port}-{to_port}) from anywhere',
                                        region=region,
                                        remediation='Limit to specific ports required for your application',
                                        account=account
                                    ))
                
                # Check if security group has no inbound rules but allows outbound
                if not sg.get('IpPermissions', []) and sg.get('IpPermissionsEgress', []):
                    # Check if it's used by any instances
                    try:
                        reservations = await ec2_client.describe_instances(
                            Filters=[{'Name': 'instance.group-id', 'Values': [sg_id]}]
                        )
                        
                        has_instances = any(
                            instance for reservation in reservations.get('Reservations', [])
                            for instance in reservation.get('Instances', [])
                            if instance.get('State', {}).get('Name') != 'terminated'
                        )
                        
                        if not has_instances and sg_name != 'default':
                            findings.append(SecurityFinding(
                                resource_type='EC2',
                                resource_id=f"{sg_name} ({sg_id})",
                                finding_type='UNUSED_SECURITY_GROUP',
                                severity='LOW',
                                description='Security group appears to be unused (no attached instances)',
                                region=region,
                                remediation='Consider removing unused security groups to reduce complexity',
                                account=account
                            ))
                    except Exception:
                        pass
                
    except Exception as e:
        rprint(f"[red]Error auditing security groups in region {region}: {e}[/red]")
    
    return findings


async def _audit_network_acls(ec2_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit Network ACLs for security misconfigurations"""
    findings = []
    
    try:
        # Get all Network ACLs
        response = await ec2_client.describe_network_acls()
        network_acls = response.get('NetworkAcls', [])
        
        for nacl in network_acls:
            nacl_id = nacl['NetworkAclId']
            is_default = nacl.get('IsDefault', False)
            vpc_id = nacl.get('VpcId', 'Unknown')
            
            # Check entries for overly permissive rules
            for entry in nacl.get('Entries', []):
                rule_action = entry.get('RuleAction', 'deny')
                rule_number = entry.get('RuleNumber', 0)
                protocol = entry.get('Protocol', '')
                cidr_block = entry.get('CidrBlock', '')
                
                # Skip the default deny rule (rule 32767)
                if rule_number == 32767:
                    continue
                
                # Check for allow rules from 0.0.0.0/0
                if (rule_action == 'allow' and 
                    cidr_block == '0.0.0.0/0' and 
                    protocol != '-1'):  # Skip the common allow all rule
                    
                    port_range = entry.get('PortRange', {})
                    from_port = port_range.get('From')
                    to_port = port_range.get('To')
                    
                    if from_port == 22 and to_port == 22:
                        findings.append(SecurityFinding(
                            resource_type='VPC',
                            resource_id=f"NACL {nacl_id}",
                            finding_type='NACL_SSH_OPEN',
                            severity='MEDIUM',
                            description='Network ACL allows SSH (port 22) from anywhere',
                            region=region,
                            remediation='Consider restricting SSH access in Network ACL',
                            account=account
                        ))
                    elif from_port == 3389 and to_port == 3389:
                        findings.append(SecurityFinding(
                            resource_type='VPC',
                            resource_id=f"NACL {nacl_id}",
                            finding_type='NACL_RDP_OPEN',
                            severity='MEDIUM',
                            description='Network ACL allows RDP (port 3389) from anywhere',
                            region=region,
                            remediation='Consider restricting RDP access in Network ACL',
                            account=account
                        ))
            
            # Check if default NACL has been modified
            if is_default:
                # Default NACLs should typically allow all traffic
                custom_rules = [e for e in nacl.get('Entries', []) if e.get('RuleNumber', 0) != 32767]
                if len(custom_rules) > 2:  # More than typical inbound/outbound allow all
                    findings.append(SecurityFinding(
                        resource_type='VPC',
                        resource_id=f"Default NACL {nacl_id}",
                        finding_type='MODIFIED_DEFAULT_NACL',
                        severity='LOW',
                        description='Default Network ACL has been modified from standard configuration',
                        region=region,
                        remediation='Consider using custom NACLs instead of modifying default NACL',
                        account=account
                    ))
    
    except Exception as e:
        rprint(f"[red]Error auditing Network ACLs in region {region}: {e}[/red]")
    
    return findings


async def _audit_vpcs(ec2_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit VPCs for security configurations"""
    findings = []
    
    try:
        # Get all VPCs
        response = await ec2_client.describe_vpcs()
        vpcs = response.get('Vpcs', [])
        
        for vpc in vpcs:
            vpc_id = vpc['VpcId']
            is_default = vpc.get('IsDefault', False)
            
            # Check VPC Flow Logs
            try:
                flow_logs_response = await ec2_client.describe_flow_logs(
                    Filters=[
                        {'Name': 'resource-id', 'Values': [vpc_id]},
                        {'Name': 'resource-type', 'Values': ['VPC']}
                    ]
                )
                
                active_flow_logs = [
                    fl for fl in flow_logs_response.get('FlowLogs', [])
                    if fl.get('FlowLogStatus') == 'ACTIVE'
                ]
                
                if not active_flow_logs:
                    findings.append(SecurityFinding(
                        resource_type='VPC',
                        resource_id=vpc_id,
                        finding_type='NO_FLOW_LOGS',
                        severity='MEDIUM',
                        description='VPC does not have Flow Logs enabled for network monitoring',
                        region=region,
                        remediation='Enable VPC Flow Logs to monitor network traffic',
                        account=account
                    ))
            except Exception:
                pass
            
            # Check for Internet Gateways
            try:
                igw_response = await ec2_client.describe_internet_gateways(
                    Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
                )
                
                internet_gateways = igw_response.get('InternetGateways', [])
                
                if internet_gateways and not is_default:
                    # This is not necessarily a finding, but worth noting for security review
                    findings.append(SecurityFinding(
                        resource_type='VPC',
                        resource_id=vpc_id,
                        finding_type='INTERNET_GATEWAY_ATTACHED',
                        severity='LOW',
                        description='VPC has Internet Gateway attached - ensure proper subnet isolation',
                        region=region,
                        remediation='Review public/private subnet configuration and routing',
                        account=account
                    ))
            except Exception:
                pass
            
            # Check DHCP Options
            dhcp_options_id = vpc.get('DhcpOptionsId')
            if dhcp_options_id and dhcp_options_id != 'default':
                try:
                    dhcp_response = await ec2_client.describe_dhcp_options(
                        DhcpOptionsIds=[dhcp_options_id]
                    )
                    
                    dhcp_options = dhcp_response.get('DhcpOptions', [])
                    if dhcp_options:
                        # Check for custom DNS servers
                        for option_set in dhcp_options:
                            for config in option_set.get('DhcpConfigurations', []):
                                if config.get('Key') == 'domain-name-servers':
                                    values = [v.get('Value') for v in config.get('Values', [])]
                                    if 'AmazonProvidedDNS' not in values:
                                        findings.append(SecurityFinding(
                                            resource_type='VPC',
                                            resource_id=vpc_id,
                                            finding_type='CUSTOM_DNS_SERVERS',
                                            severity='LOW',
                                            description='VPC uses custom DNS servers instead of Amazon provided',
                                            region=region,
                                            remediation='Verify custom DNS servers are secure and reliable',
                                            account=account
                                        ))
                except Exception:
                    pass
    
    except Exception as e:
        rprint(f"[red]Error auditing VPCs in region {region}: {e}[/red]")
    
    return findings


async def _audit_subnets(ec2_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit Subnets for security configurations"""
    findings = []
    
    try:
        # Get all subnets
        response = await ec2_client.describe_subnets()
        subnets = response.get('Subnets', [])
        
        for subnet in subnets:
            subnet_id = subnet['SubnetId']
            vpc_id = subnet.get('VpcId', 'Unknown')
            availability_zone = subnet.get('AvailabilityZone', 'Unknown')
            map_public_ip = subnet.get('MapPublicIpOnLaunch', False)
            
            # Check for auto-assign public IP
            if map_public_ip:
                # Check if this is actually a public subnet (has route to IGW)
                try:
                    # Get route table for this subnet
                    route_tables_response = await ec2_client.describe_route_tables(
                        Filters=[
                            {'Name': 'association.subnet-id', 'Values': [subnet_id]}
                        ]
                    )
                    
                    route_tables = route_tables_response.get('RouteTables', [])
                    
                    # If no explicit association, check main route table for the VPC
                    if not route_tables:
                        route_tables_response = await ec2_client.describe_route_tables(
                            Filters=[
                                {'Name': 'vpc-id', 'Values': [vpc_id]},
                                {'Name': 'association.main', 'Values': ['true']}
                            ]
                        )
                        route_tables = route_tables_response.get('RouteTables', [])
                    
                    has_igw_route = False
                    for route_table in route_tables:
                        for route in route_table.get('Routes', []):
                            if (route.get('DestinationCidrBlock') == '0.0.0.0/0' and 
                                route.get('GatewayId', '').startswith('igw-')):
                                has_igw_route = True
                                break
                    
                    if has_igw_route:
                        findings.append(SecurityFinding(
                            resource_type='VPC',
                            resource_id=f"Subnet {subnet_id}",
                            finding_type='PUBLIC_SUBNET_AUTO_IP',
                            severity='MEDIUM',
                            description='Public subnet automatically assigns public IP addresses',
                            region=region,
                            remediation='Consider disabling auto-assign public IP and use explicit allocation',
                            account=account
                        ))
                    else:
                        findings.append(SecurityFinding(
                            resource_type='VPC',
                            resource_id=f"Subnet {subnet_id}",
                            finding_type='PRIVATE_SUBNET_AUTO_IP',
                            severity='HIGH',
                            description='Private subnet configured to auto-assign public IPs',
                            region=region,
                            remediation='Disable auto-assign public IP for private subnets',
                            account=account
                        ))
                        
                except Exception:
                    pass
    
    except Exception as e:
        rprint(f"[red]Error auditing subnets in region {region}: {e}[/red]")
    
    return findings


async def audit_compute_security(regions: List[str] = None, all_regions: bool = True, account: str = None) -> List[SecurityFinding]:
    """Audit compute security - EC2, Lambda, and Container security"""
    findings = []
    
    if not regions:
        if all_regions:
            # Get all available regions
            session = aioboto3.Session()
            async with session.client('ec2', region_name='us-east-1') as ec2_client:
                regions_response = await ec2_client.describe_regions()
                regions = [region['RegionName'] for region in regions_response['Regions']]
        else:
            regions = ['us-east-1']  # Default region
    
    for region in regions:
        region_findings = await _audit_compute_security_region(region, account)
        findings.extend(region_findings)
    
    return findings


async def _audit_compute_security_region(region: str, account: str = None) -> List[SecurityFinding]:
    """Audit compute security for a specific region"""
    findings = []
    
    try:
        # Create session with the provided account/profile
        if account:
            session = aioboto3.Session(profile_name=account)
        else:
            session = aioboto3.Session()
        
        # Audit EC2 instances
        async with session.client('ec2', region_name=region) as ec2_client:
            ec2_findings = await _audit_ec2_instances(ec2_client, region, account)
            findings.extend(ec2_findings)
        
        # Audit Lambda functions
        async with session.client('lambda', region_name=region) as lambda_client:
            lambda_findings = await _audit_lambda_functions(lambda_client, region, account)
            findings.extend(lambda_findings)
        
        # Audit ECS clusters and services
        async with session.client('ecs', region_name=region) as ecs_client:
            ecs_findings = await _audit_ecs_security(ecs_client, region, account)
            findings.extend(ecs_findings)
            
    except Exception as e:
        rprint(f"[red]Error auditing compute security in region {region}: {e}[/red]")
    
    return findings


async def _audit_ec2_instances(ec2_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit EC2 instances for security misconfigurations"""
    findings = []
    
    try:
        # Get all EC2 instances
        paginator = ec2_client.get_paginator('describe_instances')
        
        async for page in paginator.paginate():
            reservations = page.get('Reservations', [])
            
            for reservation in reservations:
                instances = reservation.get('Instances', [])
                
                for instance in instances:
                    instance_id = instance.get('InstanceId', 'Unknown')
                    instance_state = instance.get('State', {}).get('Name', 'unknown')
                    
                    # Skip terminated instances
                    if instance_state == 'terminated':
                        continue
                    
                    # Check for public IP exposure
                    public_ip = instance.get('PublicIpAddress')
                    public_dns = instance.get('PublicDnsName')
                    
                    if public_ip or public_dns:
                        # Check if instance has restrictive security groups
                        security_groups = instance.get('SecurityGroups', [])
                        has_restrictive_sg = False
                        
                        for sg in security_groups:
                            sg_id = sg.get('GroupId')
                            try:
                                sg_details = await ec2_client.describe_security_groups(GroupIds=[sg_id])
                                sg_rules = sg_details['SecurityGroups'][0].get('IpPermissions', [])
                                
                                # Check if any rule allows SSH/RDP from anywhere
                                for rule in sg_rules:
                                    protocol = rule.get('IpProtocol', '')
                                    from_port = rule.get('FromPort')
                                    to_port = rule.get('ToPort')
                                    
                                    if ((protocol == 'tcp' and from_port == 22 and to_port == 22) or
                                        (protocol == 'tcp' and from_port == 3389 and to_port == 3389)):
                                        
                                        for ip_range in rule.get('IpRanges', []):
                                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                                findings.append(SecurityFinding(
                                                    resource_type='EC2',
                                                    resource_id=instance_id,
                                                    finding_type='PUBLIC_INSTANCE_OPEN_ACCESS',
                                                    severity='HIGH',
                                                    description=f'Public EC2 instance allows {"SSH" if from_port == 22 else "RDP"} from anywhere',
                                                    region=region,
                                                    remediation='Restrict security group rules or move to private subnet',
                                                    account=account
                                                ))
                            except Exception:
                                continue
                        
                        # General public IP exposure warning
                        findings.append(SecurityFinding(
                            resource_type='EC2',
                            resource_id=instance_id,
                            finding_type='PUBLIC_IP_EXPOSURE',
                            severity='MEDIUM',
                            description='EC2 instance has public IP address - review necessity',
                            region=region,
                            remediation='Consider using private subnets with NAT Gateway if public access not required',
                            account=account
                        ))
                    
                    # Check IMDSv2 enforcement
                    metadata_options = instance.get('MetadataOptions', {})
                    http_tokens = metadata_options.get('HttpTokens', 'optional')
                    
                    if http_tokens != 'required':
                        findings.append(SecurityFinding(
                            resource_type='EC2',
                            resource_id=instance_id,
                            finding_type='IMDSV2_NOT_ENFORCED',
                            severity='MEDIUM',
                            description='EC2 instance does not enforce IMDSv2 (Instance Metadata Service v2)',
                            region=region,
                            remediation='Enable IMDSv2 enforcement to prevent SSRF attacks',
                            account=account
                        ))
                    
                    # Check for instances using default security group
                    for sg in security_groups:
                        if sg.get('GroupName') == 'default':
                            findings.append(SecurityFinding(
                                resource_type='EC2',
                                resource_id=instance_id,
                                finding_type='DEFAULT_SECURITY_GROUP',
                                severity='LOW',
                                description='EC2 instance uses default security group',
                                region=region,
                                remediation='Create custom security groups with least privilege access',
                                account=account
                            ))
                    
                    # Check for instances without key pairs (if running)
                    if instance_state == 'running' and not instance.get('KeyName'):
                        findings.append(SecurityFinding(
                            resource_type='EC2',
                            resource_id=instance_id,
                            finding_type='NO_KEY_PAIR',
                            severity='LOW',
                            description='Running EC2 instance has no key pair assigned',
                            region=region,
                            remediation='Assign key pair for secure access or use Systems Manager Session Manager',
                            account=account
                        ))
                    
                    # Check for public AMI usage
                    image_id = instance.get('ImageId')
                    if image_id:
                        try:
                            image_details = await ec2_client.describe_images(ImageIds=[image_id])
                            if image_details.get('Images'):
                                image = image_details['Images'][0]
                                if image.get('Public', False):
                                    findings.append(SecurityFinding(
                                        resource_type='EC2',
                                        resource_id=instance_id,
                                        finding_type='PUBLIC_AMI_USAGE',
                                        severity='LOW',
                                        description=f'EC2 instance uses public AMI: {image_id}',
                                        region=region,
                                        remediation='Consider using private AMIs or verified public AMIs from trusted sources',
                                        account=account
                                    ))
                        except Exception:
                            # AMI might not exist anymore or access denied
                            pass
                            
    except Exception as e:
        rprint(f"[red]Error auditing EC2 instances in region {region}: {e}[/red]")
    
    return findings


async def _audit_lambda_functions(lambda_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit Lambda functions for security misconfigurations"""
    findings = []
    
    try:
        # Get all Lambda functions
        paginator = lambda_client.get_paginator('list_functions')
        
        async for page in paginator.paginate():
            functions = page.get('Functions', [])
            
            for function in functions:
                function_name = function.get('FunctionName', 'Unknown')
                function_arn = function.get('FunctionArn', '')
                
                # Check function permissions/policy
                try:
                    policy_response = await lambda_client.get_policy(FunctionName=function_name)
                    policy = policy_response.get('Policy', '')
                    
                    # Check for overly permissive policies
                    if '"Principal": "*"' in policy:
                        findings.append(SecurityFinding(
                            resource_type='Lambda',
                            resource_id=function_name,
                            finding_type='PUBLIC_LAMBDA_FUNCTION',
                            severity='HIGH',
                            description='Lambda function allows public access via wildcard principal',
                            region=region,
                            remediation='Restrict function policy to specific principals',
                            account=account
                        ))
                        
                except Exception:
                    # No policy attached or access denied - this is actually good
                    pass
                
                # Check environment variables encryption
                environment = function.get('Environment', {})
                if environment.get('Variables') and not environment.get('KMSKeyArn'):
                    findings.append(SecurityFinding(
                        resource_type='Lambda',
                        resource_id=function_name,
                        finding_type='UNENCRYPTED_ENV_VARS',
                        severity='MEDIUM',
                        description='Lambda function environment variables are not encrypted with customer KMS key',
                        region=region,
                        remediation='Enable KMS encryption for environment variables',
                        account=account
                    ))
                
                # Check VPC configuration
                vpc_config = function.get('VpcConfig', {})
                if not vpc_config.get('VpcId'):
                    # Function not in VPC - could be intentional, but worth noting
                    findings.append(SecurityFinding(
                        resource_type='Lambda',
                        resource_id=function_name,
                        finding_type='LAMBDA_NOT_IN_VPC',
                        severity='LOW',
                        description='Lambda function is not configured to run in VPC',
                        region=region,
                        remediation='Consider VPC configuration if function needs to access VPC resources securely',
                        account=account
                    ))
                
                # Check dead letter queue configuration
                dead_letter_config = function.get('DeadLetterConfig', {})
                if not dead_letter_config.get('TargetArn'):
                    findings.append(SecurityFinding(
                        resource_type='Lambda',
                        resource_id=function_name,
                        finding_type='NO_DEAD_LETTER_QUEUE',
                        severity='LOW',
                        description='Lambda function does not have dead letter queue configured',
                        region=region,
                        remediation='Configure dead letter queue for error handling and monitoring',
                        account=account
                    ))
                
                # Check function execution role permissions
                role_arn = function.get('Role', '')
                if role_arn:
                    # Extract role name from ARN
                    role_name = role_arn.split('/')[-1] if '/' in role_arn else role_arn
                    
                    # Check if role has admin permissions (this would require IAM client)
                    # For now, we'll flag functions with roles that contain 'admin' in the name
                    if 'admin' in role_name.lower():
                        findings.append(SecurityFinding(
                            resource_type='Lambda',
                            resource_id=function_name,
                            finding_type='OVERPRIVILEGED_EXECUTION_ROLE',
                            severity='MEDIUM',
                            description=f'Lambda function uses potentially overprivileged execution role: {role_name}',
                            region=region,
                            remediation='Review and apply least privilege principle to execution role',
                            account=account
                        ))
                
                # Check runtime version
                runtime = function.get('Runtime', '')
                if runtime:
                    # Flag deprecated runtimes (this list should be updated periodically)
                    deprecated_runtimes = [
                        'python2.7', 'python3.6', 'nodejs8.10', 'nodejs10.x', 
                        'dotnetcore2.1', 'ruby2.5', 'go1.x'
                    ]
                    
                    if runtime in deprecated_runtimes:
                        findings.append(SecurityFinding(
                            resource_type='Lambda',
                            resource_id=function_name,
                            finding_type='DEPRECATED_RUNTIME',
                            severity='MEDIUM',
                            description=f'Lambda function uses deprecated runtime: {runtime}',
                            region=region,
                            remediation='Update to a supported runtime version',
                            account=account
                        ))
                        
    except Exception as e:
        rprint(f"[red]Error auditing Lambda functions in region {region}: {e}[/red]")
    
    return findings


async def _audit_ecs_security(ecs_client, region: str, account: str = None) -> List[SecurityFinding]:
    """Audit ECS clusters and services for security misconfigurations"""
    findings = []
    
    try:
        # Get all ECS clusters
        clusters_response = await ecs_client.list_clusters()
        cluster_arns = clusters_response.get('clusterArns', [])
        
        if not cluster_arns:
            return findings  # No ECS clusters in this region
        
        # Get cluster details
        clusters_details = await ecs_client.describe_clusters(clusters=cluster_arns)
        clusters = clusters_details.get('clusters', [])
        
        for cluster in clusters:
            cluster_name = cluster.get('clusterName', 'Unknown')
            cluster_arn = cluster.get('clusterArn', '')
            
            # Check container insights
            settings = cluster.get('settings', [])
            container_insights_enabled = any(
                setting.get('name') == 'containerInsights' and setting.get('value') == 'enabled'
                for setting in settings
            )
            
            if not container_insights_enabled:
                findings.append(SecurityFinding(
                    resource_type='ECS',
                    resource_id=cluster_name,
                    finding_type='CONTAINER_INSIGHTS_DISABLED',
                    severity='LOW',
                    description='ECS cluster does not have Container Insights enabled',
                    region=region,
                    remediation='Enable Container Insights for better monitoring and security visibility',
                    account=account
                ))
            
            # Get services in this cluster
            try:
                services_response = await ecs_client.list_services(cluster=cluster_arn)
                service_arns = services_response.get('serviceArns', [])
                
                if service_arns:
                    services_details = await ecs_client.describe_services(
                        cluster=cluster_arn,
                        services=service_arns
                    )
                    services = services_details.get('services', [])
                    
                    for service in services:
                        service_name = service.get('serviceName', 'Unknown')
                        
                        # Check task definition
                        task_definition_arn = service.get('taskDefinition', '')
                        if task_definition_arn:
                            try:
                                task_def_response = await ecs_client.describe_task_definition(
                                    taskDefinition=task_definition_arn
                                )
                                task_definition = task_def_response.get('taskDefinition', {})
                                
                                # Check if task definition requires privileged containers
                                container_definitions = task_definition.get('containerDefinitions', [])
                                for container in container_definitions:
                                    if container.get('privileged', False):
                                        findings.append(SecurityFinding(
                                            resource_type='ECS',
                                            resource_id=f"{cluster_name}/{service_name}",
                                            finding_type='PRIVILEGED_CONTAINER',
                                            severity='HIGH',
                                            description=f'ECS service uses privileged container: {container.get("name", "unknown")}',
                                            region=region,
                                            remediation='Remove privileged flag unless absolutely necessary',
                                            account=account
                                        ))
                                    
                                    # Check for containers running as root
                                    if container.get('user') == 'root' or not container.get('user'):
                                        findings.append(SecurityFinding(
                                            resource_type='ECS',
                                            resource_id=f"{cluster_name}/{service_name}",
                                            finding_type='CONTAINER_RUNNING_AS_ROOT',
                                            severity='MEDIUM',
                                            description=f'ECS container may be running as root: {container.get("name", "unknown")}',
                                            region=region,
                                            remediation='Configure container to run as non-root user',
                                            account=account
                                        ))
                                
                                # Check network mode
                                network_mode = task_definition.get('networkMode', 'bridge')
                                if network_mode == 'host':
                                    findings.append(SecurityFinding(
                                        resource_type='ECS',
                                        resource_id=f"{cluster_name}/{service_name}",
                                        finding_type='HOST_NETWORK_MODE',
                                        severity='MEDIUM',
                                        description='ECS task uses host network mode',
                                        region=region,
                                        remediation='Consider using awsvpc network mode for better isolation',
                                        account=account
                                    ))
                                    
                            except Exception:
                                continue
                                
            except Exception:
                continue
                
    except Exception as e:
        rprint(f"[red]Error auditing ECS security in region {region}: {e}[/red]")
    
    return findings 