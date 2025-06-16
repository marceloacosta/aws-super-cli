"""
Executive HTML Report Generator for AWS Cost Optimization
Generates professional HTML reports suitable for CFO/executive presentation.
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .cost_optimization import OptimizationRecommendation


class ExecutiveReportGenerator:
    """Generate professional HTML reports for executive presentation"""
    
    def __init__(self, output_dir: str = "~/aws-savings"):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_executive_report(
        self,
        recommendations: List[OptimizationRecommendation],
        spend_analysis: Dict[str, Any],
        account_info: Dict[str, Any],
        report_title: str = "AWS Cost Optimization Executive Report"
    ) -> str:
        """Generate comprehensive executive HTML report"""
        
        # Calculate key metrics
        total_savings = sum(rec.estimated_savings for rec in recommendations)
        total_current_cost = spend_analysis.get('total_cost', 0)
        
        # Group recommendations by service
        recommendations_by_service = self._group_recommendations_by_service(recommendations)
        
        # Get top recommendations
        top_recommendations = sorted(recommendations, key=lambda x: x.estimated_savings, reverse=True)[:5]
        
        # Generate HTML content
        html_content = self._generate_html_report(
            account_info=account_info,
            report_title=report_title,
            total_savings=total_savings,
            total_current_cost=total_current_cost,
            recommendations_count=len(recommendations),
            top_recommendations=top_recommendations,
            recommendations_by_service=recommendations_by_service,
            spend_analysis=spend_analysis
        )
        
        # Save to file
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = self.output_dir / f"executive-report-{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return str(filename)
    
    def _group_recommendations_by_service(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, List[OptimizationRecommendation]]:
        """Group recommendations by service for analysis"""
        grouped = {}
        for rec in recommendations:
            service = rec.service
            if service not in grouped:
                grouped[service] = []
            grouped[service].append(rec)
        return grouped
    
    def _generate_html_report(
        self,
        account_info: Dict[str, Any],
        report_title: str,
        total_savings: float,
        total_current_cost: float,
        recommendations_count: int,
        top_recommendations: List[OptimizationRecommendation],
        recommendations_by_service: Dict[str, List[OptimizationRecommendation]],
        spend_analysis: Dict[str, Any]
    ) -> str:
        """Generate the complete HTML report"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header(report_title, account_info)}
        {self._generate_executive_summary(total_savings, total_current_cost, recommendations_count)}
        {self._generate_key_metrics(total_savings, total_current_cost)}
        {self._generate_top_recommendations(top_recommendations)}
        {self._generate_service_breakdown(recommendations_by_service)}
        {self._generate_spend_analysis(spend_analysis)}
        {self._generate_implementation_roadmap(top_recommendations)}
        {self._generate_footer()}
    </div>
</body>
</html>"""

    def _get_css_styles(self) -> str:
        """Professional CSS styles for the report"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .header {
            text-align: center;
            padding: 40px 0;
            border-bottom: 3px solid #007bff;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 2.5em;
            color: #007bff;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 20px;
        }
        
        .header .account-info {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            display: inline-block;
        }
        
        .executive-summary {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        
        .executive-summary h2 {
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .executive-summary p {
            font-size: 1.1em;
            line-height: 1.8;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            border-left: 5px solid #007bff;
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 10px;
        }
        
        .metric-label {
            font-size: 1.1em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #007bff;
        }
        
        .recommendations-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .recommendations-table th {
            background-color: #007bff;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }
        
        .recommendations-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        
        .recommendations-table tr:hover {
            background-color: #f8f9fa;
        }
        
        .confidence-high { color: #28a745; font-weight: bold; }
        .confidence-medium { color: #ffc107; font-weight: bold; }
        .confidence-low { color: #dc3545; font-weight: bold; }
        
        .savings-amount {
            font-weight: bold;
            color: #28a745;
            font-size: 1.1em;
        }
        
        .service-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .service-card h3 {
            color: #007bff;
            margin-bottom: 15px;
        }
        
        .roadmap {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 12px;
        }
        
        .roadmap-item {
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 5px solid #007bff;
        }
        
        .roadmap-item h4 {
            color: #007bff;
            margin-bottom: 10px;
        }
        
        .footer {
            text-align: center;
            padding: 30px 0;
            border-top: 2px solid #eee;
            margin-top: 40px;
            color: #666;
        }
        
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
        }
        """

    def _generate_header(self, title: str, account_info: Dict[str, Any]) -> str:
        """Generate report header"""
        current_date = datetime.now().strftime("%B %d, %Y")
        account_id = account_info.get('account_id', 'Unknown')
        
        return f"""
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">Cost Optimization Analysis & Recommendations</div>
            <div class="account-info">
                <strong>AWS Account:</strong> {account_id} | <strong>Report Date:</strong> {current_date}
            </div>
        </div>
        """

    def _generate_executive_summary(self, total_savings: float, total_current_cost: float, recommendations_count: int) -> str:
        """Generate executive summary section"""
        roi_percentage = (total_savings / total_current_cost * 100) if total_current_cost > 0 else 0
        
        return f"""
        <div class="executive-summary">
            <h2>Executive Summary</h2>
            <p>
                Our comprehensive AWS cost optimization analysis has identified <strong>{recommendations_count} actionable opportunities</strong> 
                to reduce your monthly AWS spend by <strong>${total_savings:.2f}</strong>. 
                With current monthly costs of <strong>${total_current_cost:.2f}</strong>, these optimizations represent a potential 
                <strong>{roi_percentage:.1f}% cost reduction</strong>.
            </p>
            <p>
                The recommendations focus on rightsizing underutilized resources, implementing Reserved Instances and Savings Plans, 
                and eliminating unused resources. All recommendations include detailed implementation steps and risk assessments 
                to ensure smooth execution with minimal business impact.
            </p>
        </div>
        """

    def _generate_key_metrics(self, total_savings: float, total_current_cost: float) -> str:
        """Generate key metrics cards"""
        annual_savings = total_savings * 12
        roi_percentage = (total_savings / total_current_cost * 100) if total_current_cost > 0 else 0
        
        return f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">${total_savings:.0f}</div>
                <div class="metric-label">Monthly Savings</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${annual_savings:.0f}</div>
                <div class="metric-label">Annual Savings</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{roi_percentage:.1f}%</div>
                <div class="metric-label">Cost Reduction</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${total_current_cost:.0f}</div>
                <div class="metric-label">Current Monthly Spend</div>
            </div>
        </div>
        """

    def _generate_top_recommendations(self, top_recommendations: List[OptimizationRecommendation]) -> str:
        """Generate top 5 recommendations table"""
        if not top_recommendations:
            return ""
            
        rows = ""
        for i, rec in enumerate(top_recommendations[:5], 1):
            confidence_class = f"confidence-{rec.confidence.lower()}"
            rows += f"""
            <tr>
                <td>{i}</td>
                <td>{rec.service}</td>
                <td>{rec.resource_type}</td>
                <td>{rec.description[:80]}{'...' if len(rec.description) > 80 else ''}</td>
                <td class="savings-amount">${rec.estimated_savings:.2f}</td>
                <td class="{confidence_class}">{rec.confidence}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>Top 5 Cost Optimization Opportunities</h2>
            <table class="recommendations-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Service</th>
                        <th>Resource Type</th>
                        <th>Recommendation</th>
                        <th>Monthly Savings</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    def _generate_service_breakdown(self, recommendations_by_service: Dict[str, List[OptimizationRecommendation]]) -> str:
        """Generate service-by-service breakdown"""
        if not recommendations_by_service:
            return ""
            
        service_cards = ""
        for service, recs in recommendations_by_service.items():
            total_service_savings = sum(rec.estimated_savings for rec in recs)
            service_cards += f"""
            <div class="service-card">
                <h3>{service} ({len(recs)} recommendations)</h3>
                <p><strong>Total Potential Savings:</strong> <span class="savings-amount">${total_service_savings:.2f}/month</span></p>
                <p><strong>Key Opportunities:</strong> {', '.join(set(rec.recommendation_type for rec in recs[:3]))}</p>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>Service-by-Service Analysis</h2>
            {service_cards}
        </div>
        """

    def _generate_spend_analysis(self, spend_analysis: Dict[str, Any]) -> str:
        """Generate current spend analysis"""
        services = spend_analysis.get('services', [])[:10]  # Top 10 services
        
        if not services:
            return ""
            
        rows = ""
        for service in services:
            percentage = (service['cost'] / spend_analysis.get('total_cost', 1) * 100)
            rows += f"""
            <tr>
                <td>{service['service']}</td>
                <td>${service['cost']:.2f}</td>
                <td>{percentage:.1f}%</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>Current Spend Analysis (Top 10 Services)</h2>
            <table class="recommendations-table">
                <thead>
                    <tr>
                        <th>Service</th>
                        <th>Monthly Cost</th>
                        <th>Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    def _generate_implementation_roadmap(self, top_recommendations: List[OptimizationRecommendation]) -> str:
        """Generate implementation roadmap"""
        if not top_recommendations:
            return ""
            
        roadmap_items = ""
        for i, rec in enumerate(top_recommendations[:3], 1):
            effort_level = "Low" if rec.confidence == "HIGH" else "Medium" if rec.confidence == "MEDIUM" else "High"
            roadmap_items += f"""
            <div class="roadmap-item">
                <h4>Phase {i}: {rec.service} Optimization</h4>
                <p><strong>Savings:</strong> ${rec.estimated_savings:.2f}/month</p>
                <p><strong>Effort Level:</strong> {effort_level}</p>
                <p><strong>Key Steps:</strong> {rec.remediation_steps[0] if rec.remediation_steps else 'Review and implement optimization'}</p>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>Implementation Roadmap</h2>
            <div class="roadmap">
                {roadmap_items}
            </div>
        </div>
        """

    def _generate_footer(self) -> str:
        """Generate report footer"""
        return f"""
        <div class="footer">
            <p>Generated by AWS Super CLI on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
            <p>This report contains recommendations based on AWS Cost Optimization Hub, Trusted Advisor, and Compute Optimizer analysis.</p>
        </div>
        """


# Create global instance for CLI integration
report_generator = ExecutiveReportGenerator() 