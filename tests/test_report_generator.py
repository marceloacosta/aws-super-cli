"""
Tests for Executive HTML Report Generator
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from aws_super_cli.services.report_generator import ExecutiveReportGenerator
from aws_super_cli.services.cost_optimization import OptimizationRecommendation


class TestExecutiveReportGenerator:
    """Test cases for ExecutiveReportGenerator"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def report_generator(self, temp_output_dir):
        """Create report generator with temporary output directory"""
        return ExecutiveReportGenerator(output_dir=temp_output_dir)
    
    @pytest.fixture
    def sample_recommendations(self):
        """Create sample optimization recommendations for testing"""
        return [
            OptimizationRecommendation(
                service="EC2",
                resource_id="i-1234567890abcdef0",
                resource_type="EC2 Instance",
                recommendation_type="MigrateToGraviton",
                current_cost=100.0,
                estimated_savings=25.0,
                confidence="HIGH",
                description="Production Web Server: Migrate from t3.medium to t4g.medium (Graviton) - 25% savings",
                remediation_steps=[
                    "Review current performance metrics",
                    "Test workload compatibility with Graviton processors",
                    "Plan maintenance window for migration"
                ],
                region="us-east-1",
                account_id="123456789012",
                timestamp=datetime.now().isoformat(),
                source="cost_optimization_hub"
            ),
            OptimizationRecommendation(
                service="RDS",
                resource_id="database-1",
                resource_type="RDS Database",
                recommendation_type="PurchaseReservedInstances",
                current_cost=200.0,
                estimated_savings=50.0,
                confidence="MEDIUM",
                description="Purchase Reserved Instance: 3 db.t3.micro PostgreSQL - 25% savings",
                remediation_steps=[
                    "Analyze current usage patterns",
                    "Purchase Reserved Instance",
                    "Set up RI utilization monitoring"
                ],
                region="us-east-1",
                account_id="123456789012",
                timestamp=datetime.now().isoformat(),
                source="cost_optimization_hub"
            )
        ]
    
    @pytest.fixture
    def sample_spend_analysis(self):
        """Create sample spend analysis data for testing"""
        return {
            'total_cost': 300.0,
            'services': [
                {'service': 'EC2 - Other', 'cost': 150.0},
                {'service': 'Amazon RDS', 'cost': 100.0},
                {'service': 'Amazon S3', 'cost': 50.0}
            ],
            'analysis_date': datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_account_info(self):
        """Create sample account info for testing"""
        return {
            'account_id': '123456789012',
            'account_alias': 'test-account'
        }
    
    def test_generate_executive_report_success(self, report_generator, sample_recommendations, 
                                             sample_spend_analysis, sample_account_info):
        """Test successful executive report generation"""
        report_path = report_generator.generate_executive_report(
            recommendations=sample_recommendations,
            spend_analysis=sample_spend_analysis,
            account_info=sample_account_info,
            report_title="Test Executive Report"
        )
        
        # Verify file was created
        assert Path(report_path).exists()
        
        # Verify file content
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key elements
        assert "Test Executive Report" in content
        assert "123456789012" in content
        assert "$75" in content  # Total savings (25 + 50)
        assert "$900" in content  # Annual savings (75 * 12)
        assert "Production Web Server" in content
        assert "EC2" in content
        assert "RDS" in content
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content
    
    def test_group_recommendations_by_service(self, report_generator, sample_recommendations):
        """Test grouping recommendations by service"""
        grouped = report_generator._group_recommendations_by_service(sample_recommendations)
        
        assert "EC2" in grouped
        assert "RDS" in grouped
        assert len(grouped["EC2"]) == 1
        assert len(grouped["RDS"]) == 1
        assert grouped["EC2"][0].resource_id == "i-1234567890abcdef0"
        assert grouped["RDS"][0].resource_id == "database-1"
    
    def test_generate_html_report_structure(self, report_generator, sample_recommendations,
                                          sample_spend_analysis, sample_account_info):
        """Test HTML report structure and content"""
        html_content = report_generator._generate_html_report(
            account_info=sample_account_info,
            report_title="Test Report",
            total_savings=75.0,
            total_current_cost=300.0,
            recommendations_count=2,
            top_recommendations=sample_recommendations,
            recommendations_by_service={"EC2": [sample_recommendations[0]], "RDS": [sample_recommendations[1]]},
            spend_analysis=sample_spend_analysis
        )
        
        # Check HTML structure
        assert html_content.startswith("<!DOCTYPE html>")
        assert html_content.endswith("</html>")
        assert "<head>" in html_content
        assert "<body>" in html_content
        assert "<style>" in html_content
        
        # Check content sections
        assert "Test Report" in html_content
        assert "Executive Summary" in html_content
        assert "Top 5 Cost Optimization Opportunities" in html_content
        assert "Service-by-Service Analysis" in html_content
        assert "Implementation Roadmap" in html_content
        
        # Check metrics
        assert "$75" in html_content  # Monthly savings
        assert "$900" in html_content  # Annual savings
        assert "25.0%" in html_content  # ROI percentage
    
    def test_generate_top_recommendations_table(self, report_generator, sample_recommendations):
        """Test top recommendations table generation"""
        table_html = report_generator._generate_top_recommendations(sample_recommendations)
        
        assert "Top 5 Cost Optimization Opportunities" in table_html
        assert "recommendations-table" in table_html
        assert "EC2" in table_html
        assert "RDS" in table_html
        assert "$25.00" in table_html
        assert "$50.00" in table_html
        assert "confidence-high" in table_html
        assert "confidence-medium" in table_html
    
    def test_generate_service_breakdown(self, report_generator, sample_recommendations):
        """Test service breakdown generation"""
        grouped = report_generator._group_recommendations_by_service(sample_recommendations)
        breakdown_html = report_generator._generate_service_breakdown(grouped)
        
        assert "Service-by-Service Analysis" in breakdown_html
        assert "EC2 (1 recommendations)" in breakdown_html
        assert "RDS (1 recommendations)" in breakdown_html
        assert "$25.00/month" in breakdown_html
        assert "$50.00/month" in breakdown_html
    
    def test_generate_implementation_roadmap(self, report_generator, sample_recommendations):
        """Test implementation roadmap generation"""
        roadmap_html = report_generator._generate_implementation_roadmap(sample_recommendations)
        
        assert "Implementation Roadmap" in roadmap_html
        assert "Phase 1: EC2 Optimization" in roadmap_html
        assert "Phase 2: RDS Optimization" in roadmap_html
        assert "$25.00/month" in roadmap_html
        assert "$50.00/month" in roadmap_html
        assert "Low" in roadmap_html  # HIGH confidence maps to Low effort
        assert "Medium" in roadmap_html  # MEDIUM confidence maps to Medium effort
    
    def test_empty_recommendations(self, report_generator, sample_spend_analysis, sample_account_info):
        """Test report generation with empty recommendations"""
        report_path = report_generator.generate_executive_report(
            recommendations=[],
            spend_analysis=sample_spend_analysis,
            account_info=sample_account_info
        )
        
        # Verify file was created
        assert Path(report_path).exists()
        
        # Verify content handles empty recommendations gracefully
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "0 actionable opportunities" in content
        assert "$0" in content  # Total savings should be 0
    
    def test_css_styles_included(self, report_generator):
        """Test that CSS styles are properly included"""
        css = report_generator._get_css_styles()
        
        # Check for key CSS classes
        assert ".container" in css
        assert ".header" in css
        assert ".executive-summary" in css
        assert ".metrics-grid" in css
        assert ".recommendations-table" in css
        assert ".confidence-high" in css
        assert ".confidence-medium" in css
        assert ".confidence-low" in css
        assert "@media print" in css
    
    def test_header_generation(self, report_generator, sample_account_info):
        """Test header generation with account info"""
        header_html = report_generator._generate_header("Test Report", sample_account_info)
        
        assert "Test Report" in header_html
        assert "123456789012" in header_html
        assert "Cost Optimization Analysis & Recommendations" in header_html
        assert datetime.now().strftime("%B %d, %Y") in header_html
    
    def test_executive_summary_generation(self, report_generator):
        """Test executive summary generation"""
        summary_html = report_generator._generate_executive_summary(75.0, 300.0, 5)
        
        assert "Executive Summary" in summary_html
        assert "5 actionable opportunities" in summary_html
        assert "$75.00" in summary_html
        assert "$300.00" in summary_html
        assert "25.0% cost reduction" in summary_html  # 75/300 * 100
    
    def test_key_metrics_generation(self, report_generator):
        """Test key metrics cards generation"""
        metrics_html = report_generator._generate_key_metrics(75.0, 300.0)
        
        assert "metrics-grid" in metrics_html
        assert "$75" in metrics_html  # Monthly savings
        assert "$900" in metrics_html  # Annual savings (75 * 12)
        assert "25.0%" in metrics_html  # ROI percentage
        assert "$300" in metrics_html  # Current spend
    
    def test_footer_generation(self, report_generator):
        """Test footer generation"""
        footer_html = report_generator._generate_footer()
        
        assert "Generated by AWS Super CLI" in footer_html
        assert datetime.now().strftime("%B %d, %Y") in footer_html
        assert "Cost Optimization Hub" in footer_html
        assert "Trusted Advisor" in footer_html
        assert "Compute Optimizer" in footer_html 