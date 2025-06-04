"""S3 service operations"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from rich.table import Table
from rich.console import Console
from ..aws import aws_session


def format_bucket_data(buckets_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format S3 bucket data for display"""
    formatted_buckets = []
    
    for region, response in buckets_data.items():
        if not response or 'Buckets' not in response:
            continue
            
        for bucket in response['Buckets']:
            # Format creation date
            created = bucket.get('CreationDate')
            if created:
                if isinstance(created, datetime):
                    created_str = created.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    created_str = str(created)
            else:
                created_str = 'N/A'
            
            formatted_buckets.append({
                'Bucket Name': bucket['Name'],
                'Region': region,
                'Created': created_str,
                'Encryption': 'Unknown',  # We'll enhance this later if needed
                'Versioning': 'Unknown',  # We'll enhance this later if needed
                'Public Access': 'Unknown'  # We'll enhance this later if needed
            })
    
    return formatted_buckets


def create_s3_table(buckets: List[Dict[str, str]], columns: List[str] = None) -> Table:
    """Create a rich table for S3 buckets"""
    if not columns:
        columns = ['Bucket Name', 'Region', 'Created']
    
    table = Table(title="S3 Buckets", show_header=True, header_style="bold magenta")
    
    # Add columns
    for col in columns:
        if col == 'Bucket Name':
            table.add_column(col, style="cyan", min_width=20)
        elif col == 'Region':
            table.add_column(col, style="blue", min_width=12)
        elif col == 'Created':
            table.add_column(col, style="green", min_width=16)
        else:
            table.add_column(col, min_width=10)
    
    # Add rows
    for bucket in buckets:
        row = []
        for col in columns:
            value = bucket.get(col, 'N/A')
            row.append(value)
        table.add_row(*row)
    
    return table


async def get_bucket_regions(bucket_names: List[str]) -> Dict[str, str]:
    """Get the region for each bucket"""
    bucket_regions = {}
    
    async def get_bucket_region(bucket_name: str):
        try:
            import aioboto3
            session = aioboto3.Session()
            async with session.client('s3') as s3_client:
                response = await s3_client.get_bucket_location(Bucket=bucket_name)
                # AWS returns None for us-east-1
                region = response.get('LocationConstraint') or 'us-east-1'
                return bucket_name, region
        except Exception as e:
            # If we can't get the region, default to us-east-1
            return bucket_name, 'us-east-1'
    
    if bucket_names:
        tasks = [get_bucket_region(name) for name in bucket_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, tuple):
                bucket_name, region = result
                bucket_regions[bucket_name] = region
    
    return bucket_regions


async def list_s3_buckets(
    match: str = None,
    regions: List[str] = None,
    all_regions: bool = False
) -> List[Dict[str, str]]:
    """List S3 buckets with optional filters"""
    
    try:
        # S3 buckets are global, so we list them once
        import aioboto3
        session = aioboto3.Session()
        async with session.client('s3') as s3_client:
            response = await s3_client.list_buckets()
            buckets = response.get('Buckets', [])
        
        if not buckets:
            return []
        
        # Get bucket regions if we need to filter by region
        bucket_names = [bucket['Name'] for bucket in buckets]
        bucket_regions = await get_bucket_regions(bucket_names)
        
        # Add region information to buckets
        for bucket in buckets:
            bucket['Region'] = bucket_regions.get(bucket['Name'], 'us-east-1')
        
        # Filter by regions if specified
        if regions and not all_regions:
            buckets = [bucket for bucket in buckets if bucket['Region'] in regions]
        
        # Format the bucket data
        # We'll group by region for consistency with the formatting function
        buckets_by_region = {}
        for bucket in buckets:
            region = bucket['Region']
            if region not in buckets_by_region:
                buckets_by_region[region] = {'Buckets': []}
            buckets_by_region[region]['Buckets'].append(bucket)
        
        formatted_buckets = format_bucket_data(buckets_by_region)
        
        # Apply match filter (fuzzy search on bucket name)
        if match:
            match_lower = match.lower()
            filtered_buckets = []
            for bucket in formatted_buckets:
                if match_lower in bucket['Bucket Name'].lower():
                    filtered_buckets.append(bucket)
            formatted_buckets = filtered_buckets
        
        return formatted_buckets
        
    except Exception as e:
        # Re-raise to let CLI handle credential errors properly
        raise e 