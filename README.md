# AWS Super CLI

[![PyPI version](https://badge.fury.io/py/aws-super-cli.svg)](https://badge.fury.io/py/aws-super-cli)

## What is AWS Super CLI?

AWS Super CLI is a command-line tool for AWS security auditing, resource discovery, and advanced multi-account management. It solves the key problems engineers face:

1. **AWS security misconfigurations**: Comprehensive security auditing across S3, IAM, and network infrastructure with professional export capabilities
2. **Multi-account complexity**: Smart account categorization, health monitoring, and unified management
3. **ARN complexity**: Human-readable ARN display with smart truncation and explanation capabilities
4. **Cost optimization**: Comprehensive cost analysis with rightsizing recommendations, Savings Plans analysis, and Reserved Instance optimization

Unlike other tools that focus on single concerns, AWS Super CLI provides enterprise-grade security auditing with advanced multi-account management and cost analysis in one unified interface.

**Unique features**: 
- **Account Management** - Smart categorization, health monitoring, and nickname management across AWS accounts
- **ARN Utilities** - Human-readable ARN display with smart truncation and explanation capabilities
- **Network security auditing** - Detect SSH/RDP open to world, overly permissive security groups
- **Professional Security Reports** - Export findings to CSV, TXT, HTML, and enhanced HTML with executive summaries for compliance and reporting
- **Service-level credit usage analysis** - See exactly which AWS services consume promotional credits
- **Cost optimization recommendations** - Rightsizing, Savings Plans, Reserved Instances, and Cost Optimization Hub integration
- **Multi-account security posture** - Unified security scoring across AWS organizations

## Installation

```bash
pip install aws-super-cli
```

## Quick Start

```bash
# Smart account management
aws-super-cli accounts                    # List accounts with categorization & health

# Run comprehensive security audit
aws-super-cli audit --summary

# Generate complete executive security report (most comprehensive)
aws-super-cli audit --all-accounts --export enhanced-html -o security-report.html

# List EC2 instances across all accounts  
aws-super-cli ls ec2 --all-accounts

# Get comprehensive cost analysis with optimization recommendations
aws-super-cli cost-snapshot

# Generate professional executive report for CFO/board presentation
aws-super-cli executive-report

# Get cost summary with credit analysis
aws-super-cli cost summary

# Explain ARNs in human-readable format
aws-super-cli explain arn:aws:iam::123456789012:user/john-doe
```

## Advanced Multi-Account Management

AWS Super CLI provides advanced multi-account management with automatic categorization and health monitoring:

### Account Management Commands

```bash
aws-super-cli accounts                     # Smart account listing with health checks
aws-super-cli accounts --category production  # Filter by environment type
aws-super-cli accounts-dashboard           # Comprehensive account overview
aws-super-cli accounts-health              # Detailed health reporting
aws-super-cli accounts-nickname myprofile "Production Environment"  # Set nicknames
```

### Account Management Features

**Smart Categorization:**
- Automatic environment detection (production, staging, development, security, etc.)
- Pattern-based recognition from account names and descriptions
- Enhanced OU-based categorization for Organizations
- Manual category override capabilities

**AWS Organizations Integration:**
- Large-scale account discovery via Organizations API
- Organizational unit (OU) structure visualization
- Enhanced categorization based on OU hierarchy
- CSV export for hundreds of accounts
- Efficient handling of enterprise-scale Organizations

**Health Monitoring:**
- Real-time health checks across AWS services (EC2, IAM, S3)
- Permission validation and access testing
- Health status indicators: healthy, warning, error, unknown

**Enhanced Organization:**
- Account nicknames for better identification
- Category-based filtering and grouping
- Rich table display with comprehensive account information
- OU-aware account organization for large enterprises

### Example Account Output

```
AWS Account Management

                                     AWS Accounts & Profiles                                      
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name            ┃ Nickname     ┃ Category     ┃ Account ID     ┃ Health   ┃ Type     ┃ Description             ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ prod-account    │ Production   │ production   │ 123456789012   │ ✓ healthy│ SSO      │ Main production account │
│ staging         │ —            │ staging      │ 123456789013   │ ✓ healthy│ SSO      │ Staging environment     │
│ dev-team        │ —            │ development  │ 123456789014   │ ⚠ warning│ Profile  │ Development account     │
└─────────────────┴──────────────┴──────────────┴────────────────┴──────────┴──────────┴─────────────────────────┘

Account Summary
Total Accounts: 3
Healthy Accounts: 2 / 3

Categories:
  production: 1 accounts
  staging: 1 accounts  
  development: 1 accounts
```

## ARN Utilities

AWS Super CLI provides smart ARN handling to make long AWS resource names manageable:

### ARN Utility Commands

```bash
aws-super-cli explain arn:aws:iam::123456789012:user/john-doe  # Explain ARN components
aws-super-cli ls iam                                          # Smart ARN display (default)
aws-super-cli ls iam --show-full-arns                        # Show complete ARNs
```

### ARN Utility Features

**Smart Display:**
- Human-readable names by default (e.g., "john-doe" instead of full ARN)
- Service-specific truncation rules (IAM: 25 chars, EC2: 20 chars, S3: 30 chars)
- Full ARN access available with `--show-full-arns` flag

**ARN Explanation:**
- Break down ARN components with detailed descriptions
- Service-specific pattern matching and analysis
- Human-readable resource identification

### Example ARN Output

```bash
aws-super-cli explain arn:aws:iam::123456789012:user/john-doe

                                ARN Breakdown                                
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component  ┃ Value              ┃ Description                                                     ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Partition  │ aws                │ AWS partition (standard AWS regions)                          │
│ Service    │ iam                │ AWS Identity and Access Management                            │
│ Region     │ (empty)            │ IAM is a global service                                       │
│ Account    │ 123456789012       │ AWS account ID                                                │
│ Resource   │ user/john-doe      │ IAM user named john-doe                                       │
└────────────┴────────────────────┴─────────────────────────────────────────────────────────────┘

Human-readable name: john-doe
```

## Cost Optimization

AWS Super CLI provides comprehensive cost optimization analysis across multiple AWS services:

### Cost Optimization Commands

```bash
# Comprehensive cost analysis with optimization recommendations
aws-super-cli cost-snapshot                    # 7-day analysis with recommendations
aws-super-cli cost-snapshot --days 30          # 30-day analysis
aws-super-cli cost-snapshot --export json      # Export detailed data

# Service-specific optimization recommendations
aws-super-cli optimization-recommendations                           # All services
aws-super-cli optimization-recommendations --service cost-explorer   # Cost Explorer only
aws-super-cli optimization-recommendations --service trusted-advisor # Trusted Advisor only
aws-super-cli optimization-recommendations --service compute-optimizer # Compute Optimizer only

# Check optimization service availability
aws-super-cli optimization-readiness           # Verify service access and permissions

# Generate professional executive reports
aws-super-cli executive-report                 # Professional HTML report for CFO presentation
aws-super-cli executive-report --title "Q4 2024 AWS Cost Optimization Report" --days 90
```

### Cost Optimization Features

**Cost Explorer Integration:**
- Current spend analysis with service-level breakdown
- Rightsizing recommendations for EC2 instances with potential savings
- Savings Plans purchase recommendations with ROI analysis
- Reserved Instance recommendations with multi-year projections
- Billing credits tracking and expiry management
- Cost Optimization Hub integration for comprehensive recommendations

**Trusted Advisor Integration:**
- Cost optimization checks from AWS Support
- Idle resource identification (EC2, RDS, ELB)
- Underutilized resource recommendations
- Reserved Instance optimization suggestions

**Compute Optimizer Integration:**
- EC2 instance rightsizing with performance risk assessment
- Auto Scaling group optimization recommendations
- EBS volume optimization suggestions
- Lambda function memory optimization

**Executive Report Generation:**
- Professional HTML reports ready for CFO/board presentation
- Executive summary with key financial metrics and ROI analysis
- Service-by-service breakdown with total savings per service
- Implementation roadmap with phased approach and effort levels
- Print-ready format for PDF conversion and stakeholder distribution
- Customizable report titles and analysis periods

### Example Cost Optimization Output

```
Cost Analysis & Optimization Recommendations (Last 7 Days)

                                    Current Spend by Service                                     
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Service                    ┃ Cost (USD)     ┃ Percentage     ┃ Change vs Previous Period      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Amazon Elastic Compute... │ $245.67        │ 45.2%          │ +12.3% ↗                      │
│ Amazon Simple Storage...  │ $89.23         │ 16.4%          │ -2.1% ↘                       │
│ Amazon Relational Data... │ $67.45         │ 12.4%          │ +5.7% ↗                       │
└────────────────────────────┴────────────────┴────────────────┴────────────────────────────────┘

                                 Optimization Recommendations                                  
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Service           ┃ Recommendation Type    ┃ Potential Savings  ┃ Confidence ┃ Resources Affected ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ Cost Explorer     │ EC2 Rightsizing       │ $63.52/month       │ High       │ 3 instances        │
│ Trusted Advisor   │ Idle Load Balancers   │ $18.00/month       │ High       │ 1 load balancer    │
│ Compute Optimizer │ Instance Optimization │ $45.20/month       │ Medium     │ 5 instances        │
└───────────────────┴────────────────────────┴────────────────────┴────────────┴────────────────────┘

Total Potential Monthly Savings: $126.72
```

### Confidence Scoring System

AWS Super CLI uses intelligent confidence scoring to help prioritize optimization efforts:

**Cost Optimization Hub Confidence:**
- **HIGH**: Very Low/Low implementation effort (easy wins)
- **MEDIUM**: Medium/High implementation effort (moderate complexity)
- **LOW**: Very High implementation effort (complex changes)

**Compute Optimizer Confidence:**
- **HIGH**: Overprovisioned/Underprovisioned resources (clear optimization opportunity)
- **MEDIUM**: General optimization recommendations
- **LOW**: Already optimized resources (no change needed)

**Trusted Advisor Confidence:**
- **HIGH**: Idle resources, Reserved Instance opportunities
- **MEDIUM**: General cost optimization recommendations
- **LOW**: Low-impact optimizations

The confidence levels help you focus on high-impact, low-effort optimizations first, maximizing ROI while minimizing operational risk.
```

## Security Auditing

AWS Super CLI provides comprehensive security auditing across your AWS infrastructure:

### Basic Security Commands

```bash
aws-super-cli audit                        # Comprehensive security audit (S3, IAM, Network, GuardDuty, Config, CloudTrail, CloudWatch)
aws-super-cli audit --summary              # Quick security overview with scoring
aws-super-cli audit --all-accounts         # Security audit across all accounts
aws-super-cli audit --services network     # Network security only
aws-super-cli audit --services s3,iam      # S3 and IAM audit only
aws-super-cli audit --services guardduty   # GuardDuty threat detection only
aws-super-cli audit --services cloudtrail  # CloudTrail logging coverage only
aws-super-cli audit --services cloudwatch  # CloudWatch alarm coverage only
```

### Security Coverage

**S3 Security:**
- Public bucket detection and policy analysis
- Encryption configuration and KMS key management
- Versioning, lifecycle, and access logging verification
- Account-level and bucket-level public access blocks
- HTTPS/TLS enforcement validation

**IAM Security:**
- Overprivileged users and admin policy detection
- MFA enforcement checking across all users
- Access key age analysis and rotation recommendations
- Inactive user identification (90+ days)
- Custom policy wildcard permission detection

**Network Security:**
- Security groups with SSH/RDP open to world (0.0.0.0/0)
- Overly permissive security group rules
- Unused security groups identification
- Network ACL configuration analysis
- VPC Flow Logs status verification
- Subnet public IP auto-assignment analysis

**GuardDuty Threat Detection:**
- GuardDuty enablement status across all regions
- Active threat findings and security events
- Malicious activity detection (brute force, reconnaissance, data exfiltration)
- Compromised credential identification
- Botnet and cryptocurrency mining detection
- Severity-based threat prioritization with actionable remediation

**Config Rule Coverage:**
- Compliance rule evaluation and status
- Resource tagging and compliance status
- Non-compliant resources identification

**CloudTrail Logging Coverage:**
- CloudTrail enablement status across all AWS regions
- Multi-region trail configuration and global service events
- Trail logging status and delivery channel health
- Management event and data event logging coverage
- CloudTrail log encryption with KMS and integrity validation
- S3 bucket security for CloudTrail log storage
- Regional coverage gaps and logging blind spots

**RDS Database Security:**
- Public accessibility detection for RDS instances and clusters
- Storage encryption verification for data at rest protection
- Public snapshot exposure detection and remediation
- Multi-AZ deployment verification for high availability
- Backup retention period compliance (minimum 7 days recommended)
- Deletion protection status for accidental data loss prevention
- Performance Insights encryption with customer-managed KMS keys
- Aurora cluster CloudWatch logs export configuration
- Default parameter group usage identification

**CloudWatch Alarm Coverage:**
- Monitoring coverage analysis across EC2, RDS, Lambda, and ELB resources
- Missing alarm detection for critical infrastructure components
- Alarm state analysis (OK, ALARM, INSUFFICIENT_DATA)
- Regional monitoring gap identification
- SNS notification endpoint verification for alarm actions
- Monitoring-to-resource ratio assessment for comprehensive coverage
- Operational visibility recommendations for improved incident response

### Security Report Export

AWS Super CLI provides professional export capabilities for security audit results, verified with real AWS infrastructure:

```bash
aws-super-cli audit --export csv -o report.csv           # CSV format for spreadsheet analysis
aws-super-cli audit --export txt -o report.txt           # Text format for documentation  
aws-super-cli audit --export html -o report.html         # Professional HTML report
aws-super-cli audit --export enhanced-html -o executive-report.html  # Executive summary with compliance mapping

# Most comprehensive export for executive presentations
aws-super-cli audit --all-accounts --export enhanced-html -o complete-security-report.html

# Multi-account exports with account information
aws-super-cli audit --all-accounts --export csv -o multi-account-findings.csv
```

**Export Features:**
- **CSV Export**: Structured data for spreadsheet analysis and integration with other tools
- **TXT Export**: Human-readable text format with comprehensive summary statistics
- **HTML Export**: Professional, styled reports ready for stakeholder presentation
- **Enhanced HTML Export**: Executive summaries with compliance mapping (SOC2, CIS, NIST), risk assessment, and strategic recommendations
- **Multi-account Support**: Account information included when auditing across multiple accounts
- **Summary Statistics**: Security scores, findings breakdown, and service-level analysis
- **Remediation Guidance**: Actionable remediation steps for every finding
- **Compliance Mapping**: Framework-specific compliance status for enterprise requirements

**Real-World Verified**: Export functionality tested and verified with actual AWS account data, generating professional compliance reports from live infrastructure findings.

### Example Security Output

```
Security Audit Summary
Security Score: 65/100
Total Findings: 43
  High Risk: 14
  Medium Risk: 15  
  Low Risk: 14

Findings by Service:
  EC2: 23
  VPC: 20
```

```
┏━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Severity ┃ Service ┃ Resource                                ┃ Finding        ┃ Description                                       ┃
┡━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ HIGH     │ EC2     │ web-server-sg (sg-12345678)            │ SSH_OPEN_TO_W… │ Security group allows SSH (port 22) from anywhere │
│ HIGH     │ S3      │ my-public-bucket                        │ PUBLIC_POLICY  │ Bucket policy allows public access via wildcard    │
│ MEDIUM   │ VPC     │ vpc-12345678                           │ NO_FLOW_LOGS   │ VPC does not have Flow Logs enabled                │
└──────────┴─────────┴─────────────────────────────────────────┴────────────────┴───────────────────────────────────────────────────────┘
```

## Cost Analysis

AWS Super CLI provides comprehensive cost analysis using AWS Cost Explorer API:

### Basic Cost Commands

```bash
aws-super-cli cost summary                # Overview with trends and credit breakdown
aws-super-cli cost top-spend              # Top spending services (gross costs)
aws-super-cli cost with-credits           # Top spending services (net costs after credits)
aws-super-cli cost month                  # Current month costs (matches AWS console)
aws-super-cli cost daily --days 7         # Daily cost trends
aws-super-cli cost by-account             # Multi-account cost breakdown
```

### Credit Analysis

```bash
aws-super-cli cost credits               # Credit usage trends and burn rate
aws-super-cli cost credits-by-service    # Service-level credit breakdown
```

### Key Features

- **Gross vs Net costs**: Separate "what you'd pay" from "what you actually pay"
- **Console accuracy**: Matches AWS Billing console exactly (fixes API/console discrepancy)
- **Credit transparency**: See exactly where promotional credits are applied
- **Service-level breakdown**: Which services consume most credits with coverage percentages
- **Trend analysis**: Historical patterns and monthly forecasting

### Example Output

```
Cost Summary
Period: Last 30 days
Gross Cost (without credits): $665.75
Net Cost (with credits):      $-0.05
Credits Applied:              $665.79
Daily Average (gross):        $22.19
Trend: ↗ +123.7%
```

```
Top Services by Credit Usage
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Service                                ┃   Gross Cost ┃ Credits Applied ┃     Net Cost ┃  Coverage  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Amazon Relational Database Service     │      $366.62 │         $366.62 │       <$0.01 │   100.0%   │
│ Amazon Elastic Compute Cloud - Compute │       $89.65 │          $89.65 │        $0.00 │   100.0%   │
│ Amazon Virtual Private Cloud           │       $83.05 │          $83.05 │        $0.00 │   100.0%   │
└────────────────────────────────────────┴──────────────┴─────────────────┴──────────────┴────────────┘
```

## Supported Services

| Service | Command | Multi-Account | Security Audit | Account Management | ARN Utilities |
|---------|---------|---------------|----------------|--------------------|---------------|
| **Account Management** | `aws-super-cli accounts` | ✅ | N/A | ✅ | N/A |
| **Security Audit** | `aws-super-cli audit` | ✅ | ✅ | N/A | N/A |
| **ARN Explanation** | `aws-super-cli explain` | N/A | N/A | N/A | ✅ |
| EC2 | `aws-super-cli ls ec2` | ✅ | ✅ | N/A | ✅ |
| S3 | `aws-super-cli ls s3` | ✅ | ✅ | N/A | ✅ |
| VPC | `aws-super-cli ls vpc` | ✅ | ✅ | N/A | ✅ |
| RDS | `aws-super-cli ls rds` | ✅ | ✅ | N/A | ✅ |
| Lambda | `aws-super-cli ls lambda` | ✅ | ✅ | N/A | ✅ |
| ELB | `aws-super-cli ls elb` | ✅ | ✅ | N/A | ✅ |
| IAM | `aws-super-cli ls iam` | ✅ | ✅ | N/A | ✅ |
| CloudWatch | `aws-super-cli audit --services cloudwatch` | ✅ | ✅ | N/A | N/A |

## Multi-Account Support

aws-super-cli automatically discovers AWS profiles and provides advanced account management:

```bash
# Account management and organization
aws-super-cli accounts                     # Smart account listing with health checks
aws-super-cli accounts --category production  # Filter by environment type
aws-super-cli accounts-dashboard           # Comprehensive overview
aws-super-cli accounts-health              # Detailed health monitoring

# Multi-account operations  
aws-super-cli audit --all-accounts         # Security audit across all accounts
aws-super-cli ls ec2 --all-accounts        # Query all accessible accounts
aws-super-cli ls s3 --accounts "prod-account,staging-account"  # Query specific accounts
aws-super-cli ls rds --accounts "prod-*"   # Pattern matching
```

## Usage Examples

**Account management:**
```bash
# Smart account organization
aws-super-cli accounts                     # List with smart categorization
aws-super-cli accounts --category production  # Focus on production accounts
aws-super-cli accounts-nickname prod "Production Environment"  # Set friendly names
aws-super-cli accounts-dashboard           # Comprehensive account overview

# AWS Organizations integration (large-scale)
aws-super-cli accounts-organizations       # Discover all organization accounts
aws-super-cli accounts-organizations --show-ous  # Show OU structure
aws-super-cli accounts-organizations --export-csv org.csv  # Export to CSV
aws-super-cli accounts-organizations --health-check  # Include health checks

# Account health monitoring
aws-super-cli accounts-health              # Detailed health assessment
aws-super-cli accounts-health --explain    # Health criteria explanation
aws-super-cli accounts-health --details    # Detailed health breakdown
aws-super-cli accounts --no-health-check   # Fast listing without health checks
```

**ARN utilities:**
```bash
# Human-readable ARN display
aws-super-cli ls iam                       # Smart ARN truncation (default)
aws-super-cli ls iam --show-full-arns      # Full ARNs when needed
aws-super-cli explain arn:aws:iam::123456789012:user/john-doe  # ARN breakdown

# Service-specific ARN handling
aws-super-cli ls ec2                       # EC2 instance names (20 char limit)
aws-super-cli ls s3                        # S3 bucket names (30 char limit)
```

**Security auditing:**
```bash
# Comprehensive security audit across all services
aws-super-cli audit --summary

# Network security assessment only
aws-super-cli audit --services network

# GuardDuty threat detection only
aws-super-cli audit --services guardduty

# Multi-account security posture
aws-super-cli audit --all-accounts --summary

# Detailed security findings with remediation
aws-super-cli audit --services s3,iam,network,guardduty
```

**Resource discovery:**
```bash
# Find all running production instances
aws-super-cli ls ec2 --all-accounts --state running --match prod

# Audit IAM users across production accounts
aws-super-cli ls iam --accounts "prod-*" --iam-type users

# Find PostgreSQL databases
aws-super-cli ls rds --engine postgres --all-accounts
```

**Cost analysis & optimization:**
```bash
# Monthly financial review
aws-super-cli cost summary
aws-super-cli cost month
aws-super-cli cost credits

# Cost optimization research
aws-super-cli cost top-spend --days 7
aws-super-cli cost credits-by-service
aws-super-cli cost daily --days 30

# Multi-account cost breakdown
aws-super-cli cost by-account

# Comprehensive cost analysis with optimization recommendations
aws-super-cli cost-snapshot                    # 7-day cost analysis with recommendations
aws-super-cli cost-snapshot --days 30          # 30-day analysis
aws-super-cli cost-snapshot --export json      # Export to JSON/CSV

# Cost optimization recommendations
aws-super-cli optimization-recommendations     # All optimization services
aws-super-cli optimization-recommendations --service cost-explorer  # Cost Explorer only
aws-super-cli optimization-recommendations --service trusted-advisor # Trusted Advisor only
aws-super-cli optimization-recommendations --service compute-optimizer # Compute Optimizer only

# Optimization readiness check
aws-super-cli optimization-readiness           # Check service availability
```

## Why AWS Super CLI?

| Feature | AWS CLI v2 | AWS Super CLI | Other Tools |
|---------|------------|------|-------------|
| Account management | None | Smart categorization & health | None |
| ARN utilities | None | Human-readable display | None |
| Security auditing | None | Comprehensive | Basic/None |
| Network security analysis | None | Advanced | Limited |
| Multi-account queries | Manual switching | Automatic parallel | Varies |
| Output format | JSON only | Rich tables | Varies |
| Cost analysis | None | Advanced | Basic |
| Cost optimization | None | Comprehensive | Limited |
| Credit tracking | None | Service-level | None |
| Setup complexity | Medium | Zero config | High |

**AWS Super CLI is the only tool that provides comprehensive account management, ARN utilities, security auditing, and advanced cost optimization with rightsizing recommendations.**

## Technical Details

### Cost Explorer Integration

AWS Super CLI fixes a major discrepancy between AWS Cost Explorer API and the AWS Console. The console excludes credits by default, but the API includes them, causing confusion. AWS Super CLI handles this correctly and provides both views.

### Multi-Account Architecture

- Automatically discovers profiles from `~/.aws/config` and `~/.aws/credentials`
- Executes API calls in parallel across accounts and regions
- Handles AWS SSO, IAM roles, and standard credentials
- Respects rate limits and implements proper error handling

### Performance

- Parallel API calls across accounts/regions
- Efficient data aggregation and formatting
- Minimal API requests (most resource listing is free)
- Cost Explorer API usage: ~$0.01 per cost analysis command

## Configuration

AWS Super CLI uses your existing AWS configuration. No additional setup required.

Supports:
- AWS profiles
- AWS SSO
- IAM roles
- Environment variables
- EC2 instance profiles

## Requirements

- Python 3.8+
- AWS credentials configured
- Permissions:
  - **Security auditing**: `ec2:Describe*`, `s3:GetBucket*`, `s3:GetPublicAccessBlock`, `iam:List*`, `iam:Get*`
  - **Resource listing**: `ec2:Describe*`, `s3:List*`, `rds:Describe*`, `lambda:List*`, `elasticloadbalancing:Describe*`, `iam:List*`, `sts:GetCallerIdentity`
  - **Cost analysis**: `ce:GetCostAndUsage`, `ce:GetDimensionValues`, `ce:GetRightsizingRecommendation`, `ce:GetSavingsPlansUtilization`, `ce:GetReservationUtilization`
  - **Cost optimization**: `support:DescribeTrustedAdvisorChecks`, `compute-optimizer:GetEC2InstanceRecommendations`, `cost-optimization-hub:ListRecommendations`

## API Costs

| Operation | Cost | Commands |
|-----------|------|----------|
| Resource listing | Free | All `aws-super-cli ls` commands |
| Cost Explorer API | $0.01/request | `aws-super-cli cost` commands |

Monthly cost estimate: $0.50-2.00 for typical usage.

## Advanced Usage

**Security auditing:**
```bash
# Debug security audit issues
aws-super-cli audit --debug

# Audit specific services only  
aws-super-cli audit --services network,s3

# Regional security audit
aws-super-cli audit --region us-west-2 --services network
```

**Debugging:**
```bash
aws-super-cli cost summary --debug
aws-super-cli ls ec2 --all-accounts --debug
aws-super-cli test
```

**Filtering:**
```bash
# Fuzzy matching
aws-super-cli ls ec2 --match "web"

# Specific filters
aws-super-cli ls ec2 --state running --instance-type "t3.*"
aws-super-cli ls ec2 --tag "Environment=prod"

# Time-based cost analysis
aws-super-cli cost daily --days 14
aws-super-cli cost summary --days 90
```

## Contributing

Contributions welcome. Areas of interest:

- Additional AWS service support
- Enhanced cost analysis features
- Multi-account support for more services
- Performance optimizations

## License

Apache 2.0

---

**AWS Super CLI** - AWS security auditing, multi-account resource discovery, and service-level cost intelligence.

### Account Health Criteria

AWS Super CLI performs comprehensive health checks on each account to ensure proper access and functionality:

**✓ HEALTHY** - All services accessible:
- Authentication successful (STS get_caller_identity)
- EC2 service accessible (describe_regions)
- IAM service accessible (get_account_summary) 
- S3 service accessible (list_buckets)
- No permission restrictions detected

**⚠ WARNING** - Limited permissions:
- Basic authentication successful
- Some services have AccessDenied/UnauthorizedOperation errors
- No complete service failures

**✗ ERROR** - Major access issues:
- Authentication failures (NoCredentialsError)
- Complete service access failures
- Invalid credentials or expired tokens

**? UNKNOWN** - Health check not performed:
- Used when `--no-health-check` flag is specified
- Faster account listing without connectivity tests

Use `aws-super-cli accounts-health --explain` for detailed explanations and troubleshooting guidance.

**Enhanced Organization:**