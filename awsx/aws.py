"""AWS session management for multi-account/region operations"""

import asyncio
import logging
import os
import configparser
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import boto3
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError, TokenRetrievalError

logger = logging.getLogger(__name__)


class MultiAccountSession:
    """Manages AWS sessions across multiple accounts and profiles"""
    
    def __init__(self):
        self._profiles = None
        self._accounts = None
        
    def discover_profiles(self) -> List[Dict[str, str]]:
        """Discover all available AWS profiles"""
        if self._profiles is not None:
            return self._profiles
            
        self._profiles = []
        
        # Check AWS config file
        config_path = Path.home() / '.aws' / 'config'
        if config_path.exists():
            try:
                config = configparser.ConfigParser()
                config.read(config_path)
                
                for section_name in config.sections():
                    if section_name.startswith('profile '):
                        profile_name = section_name[8:]  # Remove 'profile ' prefix
                    elif section_name == 'default':
                        profile_name = 'default'
                    else:
                        continue
                    
                    section = config[section_name]
                    
                    # Determine profile type and details
                    profile_info = {
                        'name': profile_name,
                        'type': 'unknown',
                        'account_id': None,
                        'description': f"Profile: {profile_name}"
                    }
                    
                    if 'sso_start_url' in section:
                        profile_info['type'] = 'sso'
                        if 'sso_account_id' in section:
                            profile_info['account_id'] = section['sso_account_id']
                            profile_info['description'] = f"SSO: {profile_name} ({section['sso_account_id']})"
                    elif 'role_arn' in section:
                        profile_info['type'] = 'role'
                        # Extract account from role ARN
                        role_arn = section['role_arn']
                        if ':' in role_arn:
                            parts = role_arn.split(':')
                            if len(parts) >= 5:
                                profile_info['account_id'] = parts[4]
                                profile_info['description'] = f"Role: {profile_name} ({parts[4]})"
                    elif 'aws_access_key_id' in section or profile_name == 'default':
                        profile_info['type'] = 'credentials'
                        profile_info['description'] = f"Credentials: {profile_name}"
                    
                    self._profiles.append(profile_info)
                        
            except Exception as e:
                logger.debug(f"Error reading AWS config: {e}")
        
        # Check credentials file for additional profiles
        creds_path = Path.home() / '.aws' / 'credentials'
        if creds_path.exists():
            try:
                config = configparser.ConfigParser()
                config.read(creds_path)
                
                existing_profiles = {p['name'] for p in self._profiles}
                
                for section_name in config.sections():
                    if section_name not in existing_profiles and 'aws_access_key_id' in config[section_name]:
                        self._profiles.append({
                            'name': section_name,
                            'type': 'credentials',
                            'account_id': None,
                            'description': f"Credentials: {section_name}"
                        })
                        
            except Exception as e:
                logger.debug(f"Error reading AWS credentials: {e}")
        
        # Always ensure we have the current session
        current_session = boto3.Session()
        current_profile = current_session.profile_name or 'default'
        
        if not any(p['name'] == current_profile for p in self._profiles):
            self._profiles.append({
                'name': current_profile,
                'type': 'current',
                'account_id': None,
                'description': f"Current: {current_profile}"
            })
        
        return self._profiles
    
    async def get_account_info(self, profile_name: str) -> Optional[Dict[str, str]]:
        """Get account information for a specific profile"""
        try:
            session = boto3.Session(profile_name=profile_name if profile_name != 'default' else None)
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            
            return {
                'profile': profile_name,
                'account_id': identity['Account'],
                'arn': identity['Arn'],
                'user_id': identity['UserId']
            }
        except Exception as e:
            logger.debug(f"Error getting account info for profile {profile_name}: {e}")
            return None
    
    async def discover_accounts(self) -> List[Dict[str, str]]:
        """Discover all accessible AWS accounts across profiles"""
        if self._accounts is not None:
            return self._accounts
        
        profiles = self.discover_profiles()
        self._accounts = []
        
        # Test each profile to see if it's accessible
        async def test_profile(profile_info):
            account_info = await self.get_account_info(profile_info['name'])
            if account_info:
                return {
                    **profile_info,
                    **account_info
                }
            return None
        
        tasks = [test_profile(profile) for profile in profiles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result and not isinstance(result, Exception):
                self._accounts.append(result)
        
        return self._accounts
    
    def get_profiles_by_pattern(self, pattern: str = None) -> List[str]:
        """Get profile names matching a pattern"""
        profiles = self.discover_profiles()
        
        if not pattern:
            return [p['name'] for p in profiles]
        
        pattern_lower = pattern.lower()
        matched = []
        
        for profile in profiles:
            # Match against profile name, account ID, or description
            searchable = f"{profile['name']} {profile.get('account_id', '')} {profile['description']}".lower()
            if pattern_lower in searchable:
                matched.append(profile['name'])
        
        return matched
    
    async def call_service_multi_account(
        self,
        service: str,
        method: str,
        profiles: List[str] = None,
        regions: List[str] = None,
        **kwargs
    ) -> Dict[str, Dict[str, Any]]:
        """Make async calls across multiple accounts and regions"""
        
        if not profiles:
            # Use current profile only
            current_session = boto3.Session()
            profiles = [current_session.profile_name or 'default']
        
        if not regions:
            regions = ['us-east-1']
        
        results = {}
        
        async def call_profile_region(profile: str, region: str):
            try:
                # Create session for this specific profile
                session_kwargs = {}
                if profile != 'default':
                    session_kwargs['profile_name'] = profile
                
                session = aioboto3.Session(**session_kwargs)
                async with session.client(service, region_name=region) as client:
                    method_func = getattr(client, method)
                    response = await method_func(**kwargs)
                    
                    # Get account ID for this response
                    try:
                        boto_session = boto3.Session(**session_kwargs)
                        sts = boto_session.client('sts', region_name=region)
                        identity = sts.get_caller_identity()
                        account_id = identity['Account']
                    except:
                        account_id = 'unknown'
                    
                    return profile, region, account_id, response, None
            except Exception as e:
                logger.debug(f"Error calling {service}.{method} for profile {profile} in {region}: {e}")
                return profile, region, None, None, e
        
        # Create tasks for all profile/region combinations
        tasks = []
        for profile in profiles:
            for region in regions:
                tasks.append(call_profile_region(profile, region))
        
        # Execute all calls in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in responses:
            if isinstance(result, tuple):
                profile, region, account_id, response, error = result
                if response:
                    # Key format: account_id:region or profile:region if account unknown
                    key = f"{account_id}:{region}" if account_id else f"{profile}:{region}"
                    if key not in results:
                        results[key] = {}
                    results[key] = response
                    
                    # Also store metadata
                    if 'metadata' not in results:
                        results['metadata'] = {}
                    results['metadata'][key] = {
                        'profile': profile,
                        'region': region,
                        'account_id': account_id
                    }
        
        return results


class AWSSession:
    """Manages AWS sessions for multi-account/region operations"""
    
    def __init__(self):
        self.session = boto3.Session()
        self._accounts = None
        self._regions = None
        self._credential_source = None
        self.multi_account = MultiAccountSession()
    
    def detect_credential_source(self) -> str:
        """Detect which credential source is being used"""
        if self._credential_source:
            return self._credential_source
        
        # Check environment variables
        if os.environ.get('AWS_ACCESS_KEY_ID'):
            self._credential_source = "environment variables"
            return self._credential_source
        
        # Check for AWS profile
        profile = os.environ.get('AWS_PROFILE') or self.session.profile_name
        if profile and profile != 'default':
            self._credential_source = f"profile '{profile}'"
            return self._credential_source
        
        # Check for SSO
        try:
            creds = self.session.get_credentials()
            if creds and 'sso' in str(type(creds)).lower():
                self._credential_source = "AWS SSO"
                return self._credential_source
        except:
            pass
        
        # Check for IAM role (common in EC2/ECS)
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            if 'role' in identity.get('Arn', '').lower():
                self._credential_source = "IAM role"
                return self._credential_source
        except:
            pass
        
        # Default case
        self._credential_source = "AWS credentials (default profile)"
        return self._credential_source
    
    def get_credential_help(self, error: Exception) -> List[str]:
        """Provide helpful credential setup guidance based on the error"""
        help_messages = []
        
        if isinstance(error, NoCredentialsError):
            help_messages = [
                "💡 AWS credentials not found. Here are your options:",
                "",
                "1. AWS SSO (Recommended for organizations):",
                "   aws configure sso",
                "   aws sso login",
                "",
                "2. IAM User credentials:",
                "   aws configure",
                "   # Enter your Access Key ID and Secret Access Key",
                "",
                "3. Environment variables:",
                "   export AWS_ACCESS_KEY_ID=your-key-id",
                "   export AWS_SECRET_ACCESS_KEY=your-secret-key",
                "",
                "4. Multiple accounts? Use profiles:",
                "   aws configure --profile mycompany",
                "   export AWS_PROFILE=mycompany",
            ]
        elif "InvalidClientTokenId" in str(error) or "TokenRetrievalError" in str(error):
            credential_source = self.detect_credential_source()
            help_messages = [
                f"🔑 AWS credentials ({credential_source}) are invalid or expired.",
                "",
            ]
            
            if "sso" in credential_source.lower():
                help_messages.extend([
                    "Try refreshing your SSO session:",
                    "   aws sso login",
                ])
            elif "profile" in credential_source.lower():
                profile = credential_source.split("'")[1] if "'" in credential_source else "default"
                help_messages.extend([
                    f"Try reconfiguring your profile '{profile}':",
                    f"   aws configure --profile {profile}",
                ])
            else:
                help_messages.extend([
                    "Try reconfiguring your credentials:",
                    "   aws configure",
                ])
        elif "UnauthorizedOperation" in str(error):
            help_messages = [
                "🔒 Your AWS credentials don't have sufficient permissions.",
                "",
                "Required permissions for awsx:",
                "  • ec2:DescribeInstances",
                "  • ec2:DescribeRegions", 
                "  • ec2:DescribeVpcs",
                "  • s3:ListAllMyBuckets",
                "  • s3:GetBucketLocation",
                "  • sts:GetCallerIdentity",
                "",
                "Ask your AWS admin to grant these permissions, or use a different profile:",
                "   export AWS_PROFILE=admin-profile",
            ]
        
        return help_messages
    
    def get_current_account(self) -> Optional[str]:
        """Get the current AWS account ID"""
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            return identity['Account']
        except (ClientError, NoCredentialsError):
            return None
    
    def check_credentials(self) -> tuple[bool, Optional[str], Optional[Exception]]:
        """Check if credentials are available and working
        
        Returns:
            (has_credentials, account_id, error)
        """
        try:
            # First check if credentials exist
            creds = self.session.get_credentials()
            if not creds:
                return False, None, NoCredentialsError("No AWS credentials found")
            
            # Then check if they work
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            return True, identity['Account'], None
            
        except NoCredentialsError as e:
            return False, None, e
        except ClientError as e:
            # Credentials exist but are invalid/expired
            return True, None, e
        except Exception as e:
            return False, None, e
    
    def get_available_regions(self, service: str = 'ec2') -> List[str]:
        """Get available regions for a service"""
        if not self._regions:
            try:
                ec2 = self.session.client('ec2', region_name='us-east-1')
                response = ec2.describe_regions()
                self._regions = [region['RegionName'] for region in response['Regions']]
            except (ClientError, NoCredentialsError):
                # Fallback to common regions
                self._regions = [
                    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                    'eu-west-1', 'eu-west-2', 'eu-central-1', 'ap-south-1',
                    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
                ]
        return self._regions
    
    async def call_service_async(
        self, 
        service: str, 
        method: str, 
        regions: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make async calls to AWS service across multiple regions"""
        if not regions:
            regions = ['us-east-1']  # Default to current region
        
        results = {}
        credential_errors = []
        
        async def call_region(region: str):
            try:
                session = aioboto3.Session()
                async with session.client(service, region_name=region) as client:
                    method_func = getattr(client, method)
                    response = await method_func(**kwargs)
                    return region, response, None
            except Exception as e:
                # Check if this is a credential-related error
                error_str = str(e)
                if any(cred_error in error_str for cred_error in [
                    'InvalidClientTokenId', 'UnauthorizedOperation', 
                    'NoCredentialsError', 'TokenRetrievalError',
                    'SignatureDoesNotMatch', 'AccessDenied'
                ]):
                    return region, None, e
                else:
                    # Non-credential errors (like region not supported) - log and continue
                    logger.debug(f"Error calling {service}.{method} in {region}: {e}")
                    return region, None, None
        
        # Execute calls in parallel
        tasks = [call_region(region) for region in regions]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in responses:
            if isinstance(result, tuple):
                region, response, error = result
                if error:
                    credential_errors.append((region, error))
                elif response:
                    results[region] = response
        
        # If we have credential errors and no successful responses, raise the first credential error
        if credential_errors and not results:
            region, error = credential_errors[0]
            raise error
        
        return results


# Global session instance
aws_session = AWSSession() 