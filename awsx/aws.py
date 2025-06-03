"""AWS session management for multi-account/region operations"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
import boto3
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError, TokenRetrievalError

logger = logging.getLogger(__name__)


class AWSSession:
    """Manages AWS sessions for multi-account/region operations"""
    
    def __init__(self):
        self.session = boto3.Session()
        self._accounts = None
        self._regions = None
        self._credential_source = None
    
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