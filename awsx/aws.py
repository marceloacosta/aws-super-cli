"""AWS session management for multi-account/region operations"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import boto3
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class AWSSession:
    """Manages AWS sessions for multi-account/region operations"""
    
    def __init__(self):
        self.session = boto3.Session()
        self._accounts = None
        self._regions = None
    
    def get_current_account(self) -> Optional[str]:
        """Get the current AWS account ID"""
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            return identity['Account']
        except (ClientError, NoCredentialsError):
            return None
    
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
        
        async def call_region(region: str):
            try:
                session = aioboto3.Session()
                async with session.client(service, region_name=region) as client:
                    method_func = getattr(client, method)
                    response = await method_func(**kwargs)
                    return region, response
            except Exception as e:
                logger.debug(f"Error calling {service}.{method} in {region}: {e}")
                return region, None
        
        # Execute calls in parallel
        tasks = [call_region(region) for region in regions]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in responses:
            if isinstance(result, tuple):
                region, response = result
                if response:
                    results[region] = response
        
        return results


# Global session instance
aws_session = AWSSession() 