"""Tests for ARN Intelligence functionality"""

import pytest
from aws_super_cli.utils.arn_intelligence import arn_intelligence, ARNComponents


class TestARNIntelligence:
    """Test ARN parsing and intelligence features"""
    
    def test_parse_iam_user_arn(self):
        """Test parsing IAM user ARN"""
        arn = "arn:aws:iam::123456789012:user/john-doe"
        components = arn_intelligence.parse_arn(arn)
        
        assert components is not None
        assert components.partition == "aws"
        assert components.service == "iam"
        assert components.region == ""
        assert components.account_id == "123456789012"
        assert components.resource_type == "user"
        assert components.resource_id == "john-doe"
        assert components.resource_path is None
    
    def test_parse_ec2_instance_arn(self):
        """Test parsing EC2 instance ARN"""
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"
        components = arn_intelligence.parse_arn(arn)
        
        assert components is not None
        assert components.partition == "aws"
        assert components.service == "ec2"
        assert components.region == "us-east-1"
        assert components.account_id == "123456789012"
        assert components.resource_type == "instance"
        assert components.resource_id == "i-1234567890abcdef0"
        assert components.resource_path is None
    
    def test_parse_s3_bucket_arn(self):
        """Test parsing S3 bucket ARN (no region/account)"""
        arn = "arn:aws:s3:::my-bucket-name"
        components = arn_intelligence.parse_arn(arn)
        
        assert components is not None
        assert components.partition == "aws"
        assert components.service == "s3"
        assert components.region == ""
        assert components.account_id == ""
        assert components.resource_type == ""
        assert components.resource_id == "my-bucket-name"
        assert components.resource_path is None
    
    def test_parse_lambda_function_arn(self):
        """Test parsing Lambda function ARN with colon separator"""
        arn = "arn:aws:lambda:us-west-2:123456789012:function:my-function"
        components = arn_intelligence.parse_arn(arn)
        
        assert components is not None
        assert components.partition == "aws"
        assert components.service == "lambda"
        assert components.region == "us-west-2"
        assert components.account_id == "123456789012"
        assert components.resource_type == "function"
        assert components.resource_id == "my-function"
        assert components.resource_path is None
    
    def test_parse_invalid_arn(self):
        """Test parsing invalid ARN"""
        invalid_arn = "not-an-arn"
        components = arn_intelligence.parse_arn(invalid_arn)
        assert components is None
    
    def test_get_human_readable_name_iam_user(self):
        """Test human readable name for IAM user (no resource type)"""
        arn = "arn:aws:iam::123456789012:user/john-doe"
        human_name = arn_intelligence.get_human_readable_name(arn)
        assert human_name == "john-doe"
    
    def test_get_human_readable_name_ec2_instance(self):
        """Test human readable name for EC2 instance (with resource type)"""
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"
        human_name = arn_intelligence.get_human_readable_name(arn)
        assert human_name == "instance/i-1234567890abcdef0"
    
    def test_get_human_readable_name_s3_bucket(self):
        """Test human readable name for S3 bucket"""
        arn = "arn:aws:s3:::my-bucket-name"
        human_name = arn_intelligence.get_human_readable_name(arn)
        assert human_name == "my-bucket-name"
    
    def test_smart_truncate_short_name(self):
        """Test smart truncate with name that fits"""
        arn = "arn:aws:iam::123456789012:user/john"
        truncated = arn_intelligence.smart_truncate(arn, 20)
        assert truncated == "john"
    
    def test_smart_truncate_long_name(self):
        """Test smart truncate with name that needs truncation"""
        arn = "arn:aws:iam::123456789012:user/very-long-username-that-needs-truncation"
        truncated = arn_intelligence.smart_truncate(arn, 20)
        assert truncated == "...-needs-truncation"
        assert len(truncated) <= 20
    
    def test_smart_truncate_ec2_instance(self):
        """Test smart truncate with EC2 instance"""
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"
        truncated = arn_intelligence.smart_truncate(arn, 20)
        assert truncated == "...1234567890abcdef0"
        assert len(truncated) <= 20
    
    def test_format_arn_for_display_full(self):
        """Test format ARN for display with show_full=True"""
        arn = "arn:aws:iam::123456789012:user/john-doe"
        formatted = arn_intelligence.format_arn_for_display(arn, show_full=True)
        assert formatted == arn
    
    def test_format_arn_for_display_smart(self):
        """Test format ARN for display with smart truncation"""
        arn = "arn:aws:iam::123456789012:user/john-doe"
        formatted = arn_intelligence.format_arn_for_display(arn, show_full=False)
        assert formatted == "john-doe"
    
    def test_explain_arn_iam_user(self):
        """Test ARN explanation for IAM user"""
        arn = "arn:aws:iam::123456789012:user/john-doe"
        explanation = arn_intelligence.explain_arn(arn)
        
        assert "error" not in explanation
        assert "aws (AWS partition)" in explanation["Partition"]
        assert "iam (Identity and Access Management)" in explanation["Service"]
        assert "Global (Global service)" in explanation["Region"]
        assert "123456789012 (AWS Account ID)" in explanation["Account"]
        assert "user (IAM User)" in explanation["Resource Type"]
        assert "john-doe (Unique identifier)" in explanation["Resource ID"]
    
    def test_explain_arn_ec2_instance(self):
        """Test ARN explanation for EC2 instance"""
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"
        explanation = arn_intelligence.explain_arn(arn)
        
        assert "error" not in explanation
        assert "ec2 (Elastic Compute Cloud)" in explanation["Service"]
        assert "us-east-1 (N. Virginia)" in explanation["Region"]
        assert "instance (EC2 Instance)" in explanation["Resource Type"]
    
    def test_explain_arn_invalid(self):
        """Test ARN explanation for invalid ARN"""
        invalid_arn = "not-an-arn"
        explanation = arn_intelligence.explain_arn(invalid_arn)
        assert "error" in explanation
        assert explanation["error"] == "Invalid ARN format"
    
    def test_get_arn_pattern_matches(self):
        """Test ARN pattern matching"""
        arns = [
            "arn:aws:iam::123456789012:user/john-doe",
            "arn:aws:iam::123456789012:user/jane-smith",
            "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
            "arn:aws:s3:::my-bucket"
        ]
        
        # Test matching by service
        iam_matches = arn_intelligence.get_arn_pattern_matches(arns, "iam")
        assert len(iam_matches) == 2
        assert all("iam" in arn for arn in iam_matches)
        
        # Test matching by resource name
        john_matches = arn_intelligence.get_arn_pattern_matches(arns, "john")
        assert len(john_matches) == 1
        assert "john-doe" in john_matches[0]
        
        # Test matching by region
        us_east_matches = arn_intelligence.get_arn_pattern_matches(arns, "us-east-1")
        assert len(us_east_matches) == 1
        assert "ec2" in us_east_matches[0]
    
    def test_service_display_rules(self):
        """Test service-specific display rules"""
        # IAM should not show resource type
        iam_rules = arn_intelligence.SERVICE_DISPLAY_RULES['iam']
        assert iam_rules['show_resource_type'] is False
        assert iam_rules['preferred_length'] == 25
        
        # EC2 should show resource type
        ec2_rules = arn_intelligence.SERVICE_DISPLAY_RULES['ec2']
        assert ec2_rules['show_resource_type'] is True
        assert ec2_rules['preferred_length'] == 20
        
        # S3 should not show resource type
        s3_rules = arn_intelligence.SERVICE_DISPLAY_RULES['s3']
        assert s3_rules['show_resource_type'] is False
        assert s3_rules['preferred_length'] == 30 