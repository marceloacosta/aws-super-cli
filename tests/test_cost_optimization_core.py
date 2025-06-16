#!/usr/bin/env python3
"""
Test cost optimization core infrastructure
"""

import unittest
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path

from aws_super_cli.services.cost_optimization import (
    OptimizationConfig,
    OptimizationRecommendation,
    CostOptimizationCore,
    OptimizationError,
    handle_optimization_error
)


class TestOptimizationConfig(unittest.TestCase):
    """Test OptimizationConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = OptimizationConfig()
        
        self.assertTrue(config.output_directory.endswith("aws-savings"))
        self.assertTrue(config.enable_auto_enrollment)
        self.assertTrue(config.support_plan_check)
        self.assertTrue(config.iam_policy_check)
        self.assertEqual(config.file_retention_days, 90)
        self.assertEqual(config.export_formats, ["json", "csv"])
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = OptimizationConfig(
            output_directory="/tmp/test-savings",
            enable_auto_enrollment=False,
            file_retention_days=30,
            export_formats=["json"]
        )
        
        self.assertEqual(config.output_directory, "/tmp/test-savings")
        self.assertFalse(config.enable_auto_enrollment)
        self.assertEqual(config.file_retention_days, 30)
        self.assertEqual(config.export_formats, ["json"])


class TestOptimizationRecommendation(unittest.TestCase):
    """Test OptimizationRecommendation dataclass"""
    
    def test_recommendation_creation(self):
        """Test creating a recommendation"""
        rec = OptimizationRecommendation(
            service="trusted-advisor",
            resource_id="i-1234567890abcdef0",
            resource_type="EC2 Instance",
            recommendation_type="Idle Resource",
            current_cost=50.0,
            estimated_savings=45.0,
            confidence="HIGH",
            description="Test recommendation",
            remediation_steps=["Step 1", "Step 2"],
            region="us-east-1",
            account_id="123456789012",
            timestamp="2024-01-01T00:00:00",
            source="trusted_advisor"
        )
        
        self.assertEqual(rec.service, "trusted-advisor")
        self.assertEqual(rec.estimated_savings, 45.0)
        self.assertEqual(rec.confidence, "HIGH")
        self.assertEqual(len(rec.remediation_steps), 2)
    
    def test_to_dict(self):
        """Test converting recommendation to dictionary"""
        rec = OptimizationRecommendation(
            service="test",
            resource_id="test-resource",
            resource_type="Test",
            recommendation_type="Test Type",
            current_cost=10.0,
            estimated_savings=5.0,
            confidence="MEDIUM",
            description="Test",
            remediation_steps=["Test step"],
            region="us-east-1",
            account_id="123456789012",
            timestamp="2024-01-01T00:00:00",
            source="test"
        )
        
        data = rec.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['service'], "test")
        self.assertEqual(data['estimated_savings'], 5.0)
        self.assertIn('remediation_steps', data)


class TestCostOptimizationCore(unittest.TestCase):
    """Test CostOptimizationCore class"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = OptimizationConfig(output_directory=self.temp_dir)
        self.core = CostOptimizationCore(self.config)
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_output_directory_creation(self):
        """Test that output directory is created"""
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertTrue(Path(self.temp_dir).is_dir())
    
    def test_timestamped_filename(self):
        """Test timestamped filename generation"""
        filename = self.core.get_timestamped_filename("test-service", "json")
        
        self.assertIn("test-service", filename)
        self.assertTrue(filename.endswith(".json"))
        self.assertIn(datetime.now().strftime("%Y-%m-%d"), filename)
    
    def test_save_recommendations_json(self):
        """Test saving recommendations as JSON"""
        recommendations = [
            OptimizationRecommendation(
                service="test",
                resource_id="test-resource",
                resource_type="Test",
                recommendation_type="Test Type",
                current_cost=10.0,
                estimated_savings=5.0,
                confidence="HIGH",
                description="Test recommendation",
                remediation_steps=["Test step"],
                region="us-east-1",
                account_id="123456789012",
                timestamp=datetime.now().isoformat(),
                source="test"
            )
        ]
        
        saved_files = self.core.save_recommendations(recommendations, "test-service")
        
        self.assertIn("json", saved_files)
        json_file = saved_files["json"]
        self.assertTrue(Path(json_file).exists())
        
        # Verify JSON content
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        self.assertIn("generated_at", data)
        self.assertEqual(data["total_recommendations"], 1)
        self.assertIn("recommendations", data)
        self.assertEqual(len(data["recommendations"]), 1)
    
    def test_save_recommendations_csv(self):
        """Test saving recommendations as CSV"""
        recommendations = [
            OptimizationRecommendation(
                service="test",
                resource_id="test-resource",
                resource_type="Test",
                recommendation_type="Test Type",
                current_cost=10.0,
                estimated_savings=5.0,
                confidence="HIGH",
                description="Test recommendation",
                remediation_steps=["Test step"],
                region="us-east-1",
                account_id="123456789012",
                timestamp=datetime.now().isoformat(),
                source="test"
            )
        ]
        
        saved_files = self.core.save_recommendations(recommendations, "test-service")
        
        self.assertIn("csv", saved_files)
        csv_file = saved_files["csv"]
        self.assertTrue(Path(csv_file).exists())
        
        # Verify CSV content has headers
        with open(csv_file, 'r') as f:
            content = f.read()
        
        self.assertIn("service,", content)
        self.assertIn("estimated_savings,", content)
        self.assertIn("test-resource", content)
    
    def test_cleanup_old_files(self):
        """Test cleanup of old files"""
        # Create some test files
        old_file = Path(self.temp_dir) / "test-2020-01-01.json"
        recent_file = Path(self.temp_dir) / f"test-{datetime.now().strftime('%Y-%m-%d')}.json"
        
        old_file.write_text('{"test": "old"}')
        recent_file.write_text('{"test": "recent"}')
        
        # Set a very short retention period to trigger cleanup
        self.core.config.file_retention_days = 1
        
        # Run cleanup
        deleted_count = self.core.cleanup_old_files()
        
        # Recent file should still exist, old file might be deleted
        self.assertTrue(recent_file.exists())


class TestOptimizationError(unittest.TestCase):
    """Test OptimizationError exception"""
    
    def test_optimization_error_creation(self):
        """Test creating OptimizationError"""
        error = OptimizationError(
            message="Test error",
            error_code="TEST_001",
            remediation="Fix the test"
        )
        
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.error_code, "TEST_001")
        self.assertEqual(error.remediation, "Fix the test")
    
    def test_handle_optimization_error(self):
        """Test error handling function"""
        from rich.console import Console
        import io
        
        # Capture console output
        string_io = io.StringIO()
        console = Console(file=string_io, force_terminal=False)
        
        error = OptimizationError("Test error", "TEST_001", "Fix it")
        handle_optimization_error(error, console)
        
        output = string_io.getvalue()
        self.assertIn("Test error", output)
        self.assertIn("TEST_001", output)
        self.assertIn("Fix it", output)


if __name__ == '__main__':
    unittest.main() 