# AWS Super CLI

[![PyPI version](https://badge.fury.io/py/aws-super-cli.svg)](https://badge.fury.io/py/aws-super-cli)

## What is AWS Super CLI?

AWS Super CLI is a command-line tool for AWS security auditing, resource discovery, and cost analysis across multiple accounts. It solves three key problems engineers face:

1. **AWS security misconfigurations**: Comprehensive security auditing across S3, IAM, and network infrastructure
2. **Multi-account resource visibility**: See all your AWS resources across accounts in unified tables  
3. **Service-level cost intelligence**: Get detailed cost analysis with credit allocation per service

Unlike other tools that focus on single concerns, AWS Super CLI provides enterprise-grade security auditing with beautiful resource discovery and cost intelligence in one unified interface.

**Unique features**: 
- **Network security auditing** - Detect SSH/RDP open to world, overly permissive security groups
- **Service-level credit usage analysis** - See exactly which AWS services consume promotional credits
- **Multi-account security posture** - Unified security scoring across AWS organizations

## Installation

```bash
pip install aws-super-cli
```

## Quick Start

```bash
# Run comprehensive security audit
aws-super-cli audit --summary

# List EC2 instances across all accounts  
aws-super-cli ls ec2 --all-accounts

# Get cost summary with credit analysis
aws-super-cli cost summary

# List available AWS profiles
aws-super-cli accounts
```

## Security Auditing

AWS Super CLI provides comprehensive security auditing across your AWS infrastructure:

### Basic Security Commands

```bash
aws-super-cli audit                        # Comprehensive security audit (S3, IAM, Network)
aws-super-cli audit --summary              # Quick security overview with scoring
aws-super-cli audit --all-accounts         # Security audit across all accounts
aws-super-cli audit --services network     # Network security only
aws-super-cli audit --services s3,iam      # S3 and IAM audit only
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

**Network Security (NEW in v0.9.1):**
- Security groups with SSH/RDP open to world (0.0.0.0/0)
- Overly permissive security group rules
- Unused security groups identification
- Network ACL configuration analysis
- VPC Flow Logs status verification
- Subnet public IP auto-assignment analysis

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
│ HIGH     │ EC2     │ launch-wizard-4 (sg-0bd7faf2ca62547e9)  │ SSH_OPEN_TO_W… │ Security group allows SSH (port 22) from anywhere │
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
💰 Cost Summary
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

| Service | Command | Multi-Account | Security Audit | Filters |
|---------|---------|---------------|----------------|---------|
| **Security Audit** | `aws-super-cli audit` | ✅ | ✅ | `--services`, `--summary` |
| EC2 | `aws-super-cli ls ec2` | ✅ | ✅ | `--state`, `--instance-type`, `--tag` |
| S3 | `aws-super-cli ls s3` | | ✅ | `--match` |
| VPC | `aws-super-cli ls vpc` | | ✅ | `--match` |
| RDS | `aws-super-cli ls rds` | | | `--engine` |
| Lambda | `aws-super-cli ls lambda` | | | `--runtime` |
| ELB | `aws-super-cli ls elb` | | | `--type` |
| IAM | `aws-super-cli ls iam` | | ✅ | `--iam-type` |

## Multi-Account Support

aws-super-cli automatically discovers AWS profiles and queries them in parallel:

```bash
# Security audit across all accounts
aws-super-cli audit --all-accounts

# Query all accessible accounts
aws-super-cli ls ec2 --all-accounts

# Query specific accounts
aws-super-cli ls s3 --accounts "prod-account,staging-account"

# Pattern matching
aws-super-cli ls rds --accounts "prod-*"

# List available profiles
aws-super-cli accounts
```

## Usage Examples

**Security auditing:**
```bash
# Comprehensive security audit across all services
aws-super-cli audit --summary

# Network security assessment only
aws-super-cli audit --services network

# Multi-account security posture
aws-super-cli audit --all-accounts --summary

# Detailed security findings with remediation
aws-super-cli audit --services s3,iam,network
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

**Cost analysis:**
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
```

## Why AWS Super CLI?

| Feature | AWS CLI v2 | AWS Super CLI | Other Tools |
|---------|------------|------|-------------|
| Security auditing | None | Comprehensive | Basic/None |
| Network security analysis | None | Advanced | Limited |
| Multi-account queries | Manual switching | Automatic parallel | Varies |
| Output format | JSON only | Rich tables | Varies |
| Cost analysis | None | Advanced | Basic |
| Credit tracking | None | Service-level | None |
| Setup complexity | Medium | Zero config | High |

**AWS Super CLI is the only tool that provides comprehensive security auditing with service-level credit usage analysis.**

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
  - **Cost analysis**: `ce:GetCostAndUsage`, `ce:GetDimensionValues`

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