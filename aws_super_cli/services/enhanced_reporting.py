#!/usr/bin/env python3
"""
Enhanced Security Reporting - Enterprise-grade AWS security reports
Provides executive summaries, compliance mapping, and professional reporting
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from aws_super_cli.services.audit import SecurityFinding, get_security_summary
from aws_super_cli import __version__


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    SOC2 = "SOC2"
    CIS = "CIS AWS Foundations Benchmark"
    NIST = "NIST Cybersecurity Framework"
    ISO27001 = "ISO 27001"
    PCI_DSS = "PCI DSS"
    GDPR = "GDPR"


class RiskLevel(Enum):
    """Business risk classification"""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class ComplianceMapping:
    """Maps security findings to compliance requirements"""
    framework: ComplianceFramework
    control_id: str
    control_name: str
    description: str
    finding_types: List[str]


@dataclass
class RiskAssessment:
    """Business risk assessment for security findings"""
    finding_type: str
    business_risk: RiskLevel
    potential_impact: str
    likelihood: str
    remediation_priority: int  # 1-5, 1 being highest
    estimated_effort: str  # Hours/Days/Weeks


@dataclass
class ExecutiveSummary:
    """Executive summary data structure"""
    overall_score: int
    risk_rating: str
    total_findings: int
    critical_issues: int
    high_priority_actions: List[str]
    compliance_status: Dict[str, str]
    key_metrics: Dict[str, Any]
    recommendations: List[str]


class EnhancedSecurityReporter:
    """Enhanced enterprise security reporting system"""
    
    def __init__(self):
        self.compliance_mappings = self._init_compliance_mappings()
        self.risk_assessments = self._init_risk_assessments()
    
    def _init_compliance_mappings(self) -> List[Dict]:
        return [
            {
                "framework": "SOC2",
                "control_id": "CC6.1",
                "control_name": "Access Controls",
                "finding_types": ["SSH_OPEN_TO_WORLD", "RDP_OPEN_TO_WORLD", "PUBLIC_ACL"]
            },
            {
                "framework": "CIS", 
                "control_id": "2.1.2",
                "control_name": "S3 Public Access",
                "finding_types": ["PUBLIC_ACL", "PUBLIC_POLICY"]
            }
        ]
    
    def _init_risk_assessments(self) -> List[RiskAssessment]:
        """Initialize business risk assessments"""
        return [
            # Critical Business Risk
            RiskAssessment(
                finding_type="SSH_OPEN_TO_WORLD",
                business_risk=RiskLevel.CRITICAL,
                potential_impact="Direct server compromise, data breach, lateral movement",
                likelihood="High",
                remediation_priority=1,
                estimated_effort="1-2 hours"
            ),
            RiskAssessment(
                finding_type="RDP_OPEN_TO_WORLD",
                business_risk=RiskLevel.CRITICAL,
                potential_impact="Direct server compromise, data breach, credential theft",
                likelihood="High",
                remediation_priority=1,
                estimated_effort="1-2 hours"
            ),
            RiskAssessment(
                finding_type="PUBLIC_ACL",
                business_risk=RiskLevel.CRITICAL,
                potential_impact="Public data exposure, sensitive information leak",
                likelihood="Medium",
                remediation_priority=1,
                estimated_effort="30 minutes"
            ),
            RiskAssessment(
                finding_type="RDS_PUBLIC_ACCESS",
                business_risk=RiskLevel.CRITICAL,
                potential_impact="Database breach, customer data exposure, compliance violations",
                likelihood="Medium",
                remediation_priority=1,
                estimated_effort="2-4 hours"
            ),
            
            # High Business Risk
            RiskAssessment(
                finding_type="NO_ENCRYPTION",
                business_risk=RiskLevel.HIGH,
                potential_impact="Data exposure in case of breach, compliance violations",
                likelihood="Medium",
                remediation_priority=2,
                estimated_effort="2-8 hours"
            ),
            RiskAssessment(
                finding_type="NO_MFA",
                business_risk=RiskLevel.HIGH,
                potential_impact="Account takeover, privilege escalation",
                likelihood="Medium",
                remediation_priority=2,
                estimated_effort="15 minutes per user"
            ),
            RiskAssessment(
                finding_type="ADMIN_USER",
                business_risk=RiskLevel.HIGH,
                potential_impact="Excessive privileges, insider threat, account compromise",
                likelihood="Low",
                remediation_priority=2,
                estimated_effort="1-2 hours"
            ),
            
            # Medium Business Risk
            RiskAssessment(
                finding_type="NO_FLOW_LOGS",
                business_risk=RiskLevel.MEDIUM,
                potential_impact="Limited visibility into network activity, compliance gaps",
                likelihood="Low",
                remediation_priority=3,
                estimated_effort="30 minutes"
            ),
            RiskAssessment(
                finding_type="VERSIONING_DISABLED",
                business_risk=RiskLevel.MEDIUM,
                potential_impact="Data loss risk, limited recovery options",
                likelihood="Low",
                remediation_priority=3,
                estimated_effort="15 minutes"
            ),
            
            # Low Business Risk
            RiskAssessment(
                finding_type="OLD_ACCESS_KEY",
                business_risk=RiskLevel.LOW,
                potential_impact="Stale credentials, potential security debt",
                likelihood="Low",
                remediation_priority=4,
                estimated_effort="30 minutes"
            ),
            RiskAssessment(
                finding_type="UNUSED_SECURITY_GROUP",
                business_risk=RiskLevel.LOW,
                potential_impact="Security configuration drift, maintenance overhead",
                likelihood="Low",
                remediation_priority=5,
                estimated_effort="15 minutes"
            ),
        ]
    
    def generate_executive_summary(self, findings: List[SecurityFinding]) -> ExecutiveSummary:
        """Generate executive summary from security findings"""
        summary = get_security_summary(findings)
        score = summary['score']
        
        # Determine risk rating
        if score >= 80:
            risk_rating = "Low Risk"
        elif score >= 60:
            risk_rating = "Medium Risk"
        elif score >= 40:
            risk_rating = "High Risk"
        else:
            risk_rating = "Critical Risk"
        
        # Identify critical issues requiring immediate attention
        critical_findings = [f for f in findings if f.severity == 'HIGH']
        critical_issues = len(critical_findings)
        
        # Generate high priority actions
        high_priority_actions = []
        priority_findings = sorted(critical_findings, key=lambda x: self._get_remediation_priority(x.finding_type))[:5]
        
        for finding in priority_findings:
            action = f"Fix {finding.finding_type.replace('_', ' ').title()} in {finding.resource_type}"
            if action not in high_priority_actions:
                high_priority_actions.append(action)
        
        # Assess compliance status
        compliance_status = self._assess_compliance_status(findings)
        
        # Calculate key metrics
        key_metrics = {
            "services_audited": len(set(f.resource_type for f in findings)),
            "regions_covered": len(set(f.region for f in findings)),
            "resources_analyzed": len(set(f.resource_id for f in findings)),
            "avg_remediation_time": self._calculate_avg_remediation_time(findings),
            "compliance_score": self._calculate_compliance_score(findings)
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings, score)
        
        return ExecutiveSummary(
            overall_score=score,
            risk_rating=risk_rating,
            total_findings=len(findings),
            critical_issues=critical_issues,
            high_priority_actions=high_priority_actions,
            compliance_status=compliance_status,
            key_metrics=key_metrics,
            recommendations=recommendations
        )
    
    def _get_remediation_priority(self, finding_type: str) -> int:
        """Get remediation priority for a finding type"""
        for assessment in self.risk_assessments:
            if assessment.finding_type == finding_type:
                return assessment.remediation_priority
        return 5  # Default low priority
    
    def _assess_compliance_status(self, findings: List[SecurityFinding]) -> Dict[str, str]:
        """Assess compliance status for each framework"""
        status = {}
        
        for framework in ComplianceFramework:
            framework_findings = self._get_framework_findings(findings, framework)
            total_controls = len([m for m in self.compliance_mappings if m["framework"] == framework.value])
            affected_controls = len(set(m["control_id"] for m in framework_findings))
            
            if affected_controls == 0:
                status[framework.value] = "Compliant"
            elif affected_controls <= total_controls * 0.1:
                status[framework.value] = "Mostly Compliant"
            elif affected_controls <= total_controls * 0.3:
                status[framework.value] = "Partially Compliant"
            else:
                status[framework.value] = "Non-Compliant"
        
        return status
    
    def _get_framework_findings(self, findings: List[SecurityFinding], framework: ComplianceFramework) -> List[Dict]:
        """Get compliance mappings for findings in a specific framework"""
        framework_mappings = []
        finding_types = set(f.finding_type for f in findings)
        
        for mapping in self.compliance_mappings:
            if mapping["framework"] == framework.value:
                for finding_type in mapping["finding_types"]:
                    if finding_type in finding_types:
                        framework_mappings.append(mapping)
                        break
        
        return framework_mappings
    
    def _calculate_avg_remediation_time(self, findings: List[SecurityFinding]) -> str:
        """Calculate average remediation time"""
        total_hours = 0
        count = 0
        
        for finding in findings:
            for assessment in self.risk_assessments:
                if assessment.finding_type == finding.finding_type:
                    effort = assessment.estimated_effort
                    if "hour" in effort:
                        hours = float(effort.split("-")[0] if "-" in effort else effort.split()[0])
                        total_hours += hours
                        count += 1
                    elif "minute" in effort:
                        minutes = float(effort.split()[0])
                        total_hours += minutes / 60
                        count += 1
                    elif "day" in effort:
                        days = float(effort.split("-")[0] if "-" in effort else effort.split()[0])
                        total_hours += days * 8  # 8 hours per day
                        count += 1
                    break
        
        if count == 0:
            return "Unknown"
        
        avg_hours = total_hours / count
        if avg_hours < 1:
            return f"{int(avg_hours * 60)} minutes"
        elif avg_hours < 8:
            return f"{avg_hours:.1f} hours"
        else:
            return f"{avg_hours / 8:.1f} days"
    
    def _calculate_compliance_score(self, findings: List[SecurityFinding]) -> int:
        """Calculate overall compliance score"""
        total_controls = len(self.compliance_mappings)
        finding_types = set(f.finding_type for f in findings)
        
        violated_controls = 0
        for mapping in self.compliance_mappings:
            for finding_type in mapping["finding_types"]:
                if finding_type in finding_types:
                    violated_controls += 1
                    break
        
        compliance_score = max(0, 100 - int((violated_controls / total_controls) * 100))
        return compliance_score
    
    def _generate_recommendations(self, findings: List[SecurityFinding], score: int) -> List[str]:
        """Generate strategic recommendations based on findings"""
        recommendations = []
        
        # Score-based recommendations
        if score < 40:
            recommendations.append("Immediate security review required - multiple critical vulnerabilities detected")
            recommendations.append("Implement emergency response plan for high-risk findings")
            recommendations.append("Consider engaging external security consultants for rapid remediation")
        elif score < 60:
            recommendations.append("Prioritize remediation of high-severity findings within 30 days")
            recommendations.append("Establish regular security review cycles")
        elif score < 80:
            recommendations.append("Focus on medium-risk findings to improve security posture")
            recommendations.append("Implement security automation where possible")
        else:
            recommendations.append("Maintain current security standards and address remaining findings")
            recommendations.append("Consider advanced security monitoring and threat detection")
        
        # Finding-based recommendations
        finding_types = set(f.finding_type for f in findings)
        
        if any(ft in finding_types for ft in ['SSH_OPEN_TO_WORLD', 'RDP_OPEN_TO_WORLD', 'ALL_TRAFFIC_OPEN']):
            recommendations.append("Implement network segmentation and restrict public access")
        
        if any(ft in finding_types for ft in ['NO_MFA', 'ADMIN_USER', 'WILDCARD_POLICY']):
            recommendations.append("Strengthen identity and access management (IAM) policies")
        
        if any(ft in finding_types for ft in ['NO_ENCRYPTION', 'S3_MANAGED_ENCRYPTION']):
            recommendations.append("Implement encryption-at-rest for all sensitive data")
        
        if any(ft in finding_types for ft in ['NO_FLOW_LOGS', 'NO_ACCESS_LOGGING', 'CLOUDTRAIL_NOT_LOGGING']):
            recommendations.append("Enhance logging and monitoring capabilities")
        
        if any(ft in finding_types for ft in ['NO_GUARDDUTY_DETECTOR', 'GUARDDUTY_DETECTOR_DISABLED']):
            recommendations.append("Enable advanced threat detection services")
        
        return recommendations[:6]  # Limit to top 6 recommendations
    
    def export_enhanced_html_report(self, findings: List[SecurityFinding], filepath: str, show_account: bool = False) -> None:
        """Export enhanced HTML report with executive summary"""
        executive_summary = self.generate_executive_summary(findings)
        summary_stats = get_security_summary(findings)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Security Audit Report - Enhanced</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 20px auto; 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            text-align: center; 
            padding: 40px 20px; 
        }}
        .header h1 {{ 
            margin: 0; 
            font-size: 2.8em; 
            font-weight: 300;
        }}
        .content {{ 
            padding: 40px; 
        }}
        .executive-summary {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 40px;
            border-left: 5px solid #007bff;
        }}
        .risk-banner {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 25px;
            color: white;
            font-weight: bold;
            margin: 10px 0;
        }}
        .risk-low {{ background: #28a745; }}
        .risk-medium {{ background: #ffc107; color: #000; }}
        .risk-high {{ background: #fd7e14; }}
        .risk-critical {{ background: #dc3545; }}
        .metrics-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin: 30px 0; 
        }}
        .metric-card {{ 
            background: white; 
            border: 1px solid #e9ecef; 
            border-radius: 10px; 
            padding: 25px; 
            text-align: center; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        }}
        .metric-value {{ 
            font-size: 2.5em; 
            font-weight: bold; 
            margin: 10px 0; 
        }}
        .score-good {{ color: #28a745; }}
        .score-warning {{ color: #ffc107; }}
        .score-danger {{ color: #dc3545; }}
        .recommendations {{
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-radius: 10px;
            padding: 25px;
            margin: 30px 0;
        }}
        .findings-table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px; 
            background: white; 
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .findings-table th {{ 
            background: linear-gradient(135deg, #495057 0%, #6c757d 100%);
            color: white; 
            padding: 15px; 
            text-align: left; 
        }}
        .findings-table td {{ 
            padding: 12px 15px; 
            border-bottom: 1px solid #dee2e6; 
        }}
        .severity-high {{ color: #dc3545; font-weight: bold; }}
        .severity-medium {{ color: #fd7e14; font-weight: bold; }}
        .severity-low {{ color: #28a745; font-weight: bold; }}
        .section-header {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin: 40px 0 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AWS Security Audit Report</h1>
            <div>Enhanced Enterprise Security Assessment</div>
            <div>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="content">
            <div class="executive-summary">
                <h2>Executive Summary</h2>
                <div class="risk-banner risk-{executive_summary.risk_rating.lower().replace(' ', '-')}">{executive_summary.risk_rating}</div>
                <p>Security assessment analyzed <strong>{executive_summary.total_findings}</strong> findings across <strong>{executive_summary.key_metrics['services_audited']}</strong> AWS services. Overall security score: <strong>{executive_summary.overall_score}/100</strong></p>
                
                <div class="recommendations">
                    <h3>Strategic Recommendations</h3>
                    <ul>"""
        
        for rec in executive_summary.recommendations:
            html_content += f"<li>{rec}</li>"
        
        html_content += f"""
                    </ul>
                </div>
            </div>
            
            <h2 class="section-header">Security Metrics Dashboard</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Security Score</h3>
                    <div class="metric-value score-{'good' if executive_summary.overall_score >= 70 else 'warning' if executive_summary.overall_score >= 40 else 'danger'}">{executive_summary.overall_score}</div>
                    <small>out of 100</small>
                </div>
                <div class="metric-card">
                    <h3>Critical Findings</h3>
                    <div class="metric-value score-{'good' if summary_stats['high'] == 0 else 'danger'}">{summary_stats['high']}</div>
                    <small>requiring immediate action</small>
                </div>
                <div class="metric-card">
                    <h3>Resources Analyzed</h3>
                    <div class="metric-value score-good">{executive_summary.key_metrics['resources_analyzed']}</div>
                    <small>AWS resources</small>
                </div>
                <div class="metric-card">
                    <h3>Services Covered</h3>
                    <div class="metric-value score-good">{executive_summary.key_metrics['services_audited']}</div>
                    <small>AWS services</small>
                </div>
            </div>
            
            <h2 class="section-header">Detailed Security Findings</h2>
            <table class="findings-table">
                <thead>
                    <tr>"""
        
        if show_account:
            html_content += "<th>Account</th>"
        
        html_content += """
                        <th>Severity</th>
                        <th>Service</th>
                        <th>Resource</th>
                        <th>Finding Type</th>
                        <th>Description</th>
                        <th>Region</th>
                        <th>Remediation</th>
                    </tr>
                </thead>
                <tbody>"""
        
        # Sort findings by severity
        severity_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        sorted_findings = sorted(findings, key=lambda x: severity_order.get(x.severity, 3))
        
        for finding in sorted_findings:
            severity_class = f"severity-{finding.severity.lower()}"
            html_content += f"""
                    <tr>"""
            
            if show_account:
                html_content += f"<td>{finding.account or 'current'}</td>"
            
            html_content += f"""
                        <td class="{severity_class}">{finding.severity}</td>
                        <td>{finding.resource_type}</td>
                        <td style="max-width: 200px; word-wrap: break-word;">{finding.resource_id}</td>
                        <td>{finding.finding_type.replace('_', ' ').title()}</td>
                        <td>{finding.description}</td>
                        <td>{finding.region}</td>
                        <td>{finding.remediation or '-'}</td>
                    </tr>"""
        
        html_content += f"""
                </tbody>
            </table>
            
            <div class="executive-summary" style="margin-top: 40px;">
                <h2>Immediate Action Items</h2>
                <ol>"""
        
        for action in executive_summary.high_priority_actions:
            html_content += f"<li style='margin: 10px 0;'>{action}</li>"
        
        html_content += f"""
                </ol>
            </div>
            
            <div style="text-align: center; margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <small>Report generated by AWS Super CLI v{__version__} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        with open(filepath, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write(html_content)

    def export_compliance_report(self, findings: List[SecurityFinding], framework: ComplianceFramework, filepath: str) -> None:
        """Export compliance-specific report for a framework"""
        framework_findings = self._get_framework_findings(findings, framework)
        
        # Generate compliance-specific HTML report
        html_content = self._generate_compliance_html(findings, framework, framework_findings)
        
        with open(filepath, 'w', encoding='utf-8') as htmlfile:
            htmlfile.write(html_content)

    def _generate_compliance_html(self, findings: List[SecurityFinding], framework: ComplianceFramework, 
                                framework_mappings: List[Dict]) -> str:
        """Generate compliance-specific HTML report"""
        
        finding_types = set(f.finding_type for f in findings)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{framework.value} Compliance Report</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ color: #2c3e50; }}
        .control-section {{ margin: 30px 0; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px; }}
        .control-header {{ background: #495057; color: white; padding: 15px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }}
        .violation {{ background: #f8d7da; padding: 10px; margin: 10px 0; border-left: 4px solid #dc3545; border-radius: 4px; }}
        .compliant {{ background: #d4edda; padding: 10px; margin: 10px 0; border-left: 4px solid #28a745; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{framework.value} Compliance Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
"""
        
        # Group mappings by control
        controls = {}
        for mapping in self.compliance_mappings:
            if mapping["framework"] == framework.value:
                if mapping["control_id"] not in controls:
                    controls[mapping["control_id"]] = {
                        'name': mapping["control_name"],
                        'description': mapping["description"],
                        'mappings': []
                    }
                controls[mapping["control_id"]]['mappings'].append(mapping)
        
        # Generate control sections
        for control_id, control_data in controls.items():
            violations = []
            for mapping in control_data['mappings']:
                for finding_type in mapping["finding_types"]:
                    if finding_type in finding_types:
                        violation_count = sum(1 for f in findings if f.finding_type == finding_type)
                        violations.append({
                            'type': finding_type,
                            'count': violation_count
                        })
            
            is_compliant = len(violations) == 0
            status_class = "compliant" if is_compliant else "violation"
            status_text = "COMPLIANT" if is_compliant else "NON-COMPLIANT"
            
            html_content += f"""
        <div class="control-section">
            <div class="control-header">
                <h3>{control_id}: {control_data['name']}</h3>
                <span>Status: {status_text}</span>
            </div>
            <p>{control_data['description']}</p>
            
            <div class="{status_class}">
"""
            
            if is_compliant:
                html_content += "<strong>✓ No violations found for this control</strong>"
            else:
                html_content += "<strong>⚠ Violations found:</strong><ul>"
                for violation in violations:
                    html_content += f"<li>{violation['type'].replace('_', ' ').title()}: {violation['count']} occurrences</li>"
                html_content += "</ul>"
            
            html_content += """
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        return html_content 